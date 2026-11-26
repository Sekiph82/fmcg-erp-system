"""Audience lifecycle on Meta / Google / LinkedIn / TikTok (M49.S01.T011), on top of the M44/M47 consented audiences.

segment (mkt_audiences) -> preview (membership diff, eligibility) -> second-person approval bound to the diff hash ->
sync (create, add, remove) -> status poll / reconcile -> consent withdrawal (removed everywhere + suppression list).

Rules kept here:
- Only members with marketing consent (SUBSCRIBED, re-checked at sync time) and not on the suppression list are ever
  sent, as SHA-256 hashes. A member who withdrew consent is removed from every platform immediately (no approval
  needed: removing data is never blocked) and can never be added again.
- SIMULATED and LIVE are stored apart. LIVE needs the same switches as ad mutations (ads_service.gate) plus
  AUDIENCE_EXPORT_ENABLED. READY is only stored when the provider's own status says so.
- A local similarity score (audience_service.similar) is a local score; a provider lookalike exists only where the API
  documents one (Meta) and is created from a provider-side seed, never invented.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import event, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked
from app.models.crm import AdAccount, CRMContactConsent, MarketingAudience, MarketingAudienceMember
from app.models.m49_audiences import AudienceSuppression, AudienceSync, AudienceSyncMember
from app.models.sales import Customer
from app.services import ads_adapters as ads
from app.services import ads_service as svc
from app.services import audience_service as aus
from app.services import audience_sync_adapters as ad
from app.services.ads_adapters import AdsError
from app.services.ads_service import Refused

log = logging.getLogger(__name__)
SENT = ("IN_SYNC", "PENDING_ADD", "PENDING_REMOVE")


def _audit(db: AsyncSession, user, event: str, target_id, details: dict) -> None:
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_id=getattr(user, "id", None), actor_email=getattr(user, "email", None),
                    actor_name=getattr(user, "full_name", None), event_type=event, module="audiences",
                    target_type="audience_sync", target_id=str(target_id) if target_id else None, details=details))


def mask(email: str) -> str:
    n, _, d = email.partition("@")
    return f"{n[:1]}***@{d}"


def gate(acct: AdAccount, ctrl) -> dict:
    g = svc.gate(acct, ctrl)
    if not settings.AUDIENCE_EXPORT_ENABLED:
        g = {**g, "mode": "SIMULATED", "transport": "blocked",
             "reasons": [*g["reasons"], "AUDIENCE_EXPORT_ENABLED is off: no customer data may be shared with an ad platform."]}
    return g


async def suppressed(db: AsyncSession) -> set[str]:
    return set((await db.execute(select(AudienceSuppression.email_sha256))).scalars())


async def eligible_members(db: AsyncSession, audience: MarketingAudience) -> dict[str, dict]:
    """Consent + suppression filtered members as {email hash: hashes}. The consent check is done now, not at recompute."""
    rows = (await db.execute(select(MarketingAudienceMember.customer_id, MarketingAudienceMember.email, Customer.phone).join(
        Customer, Customer.id == MarketingAudienceMember.customer_id).where(MarketingAudienceMember.audience_id == audience.id))).all()
    ok, sup, out = await aus._consented(db), await suppressed(db), {}
    for cid, email, phone in rows:
        e = ads.hash_email(email)
        if not e or (email or "").strip().lower() not in ok or e in sup:
            continue
        out[e] = {"e": e, "p": ads.hash_phone(phone, plus=True), "pn": ads.hash_phone(phone, plus=False), "cid": str(cid),
                  "email": (email or "").strip().lower()}
    return out


async def sent_members(db: AsyncSession, sync: AudienceSync) -> dict[str, AudienceSyncMember]:
    return {m.email_sha256: m for m in (await db.execute(select(AudienceSyncMember).where(
        AudienceSyncMember.sync_id == sync.id))).scalars()}


def eligibility(provider: str, size: int) -> dict:
    low, blocking, note = ad.MINIMUMS[provider]
    ok = size >= low
    return {"minimum": low, "size_after": size, "eligible": ok, "blocking": blocking and not ok, "note": note}


async def diff(db: AsyncSession, sync: AudienceSync) -> dict:
    audience = await db.get(MarketingAudience, sync.audience_id)
    want, have = await eligible_members(db, audience), await sent_members(db, sync)
    in_sync = {h for h, m in have.items() if m.state == "IN_SYNC"}
    add = [want[h] for h in sorted(set(want) - in_sync)]
    gone = [h for h, m in have.items() if m.state in SENT and h not in want]
    keep = len(in_sync & set(want))
    if sync.kind == "LOOKALIKE":
        key = [sync.provider, str(sync.account_id), str(sync.origin_sync_id), json.dumps(sync.spec, sort_keys=True)]
    else:
        key = [sync.provider, str(sync.account_id), sync.name, *[a["e"] for a in add], "-", *gone]
    return {"add": add, "remove": gone, "keep": keep, "size_after": keep + len(add),
            "hash": hashlib.sha256("|".join(key).encode()).hexdigest()}


async def preview(db: AsyncSession, sync: AudienceSync) -> dict:
    d = await diff(db, sync)
    audience = await db.get(MarketingAudience, sync.audience_id)
    return {"add": len(d["add"]), "remove": len(d["remove"]), "unchanged": d["keep"], "size_after": d["size_after"],
            "blocked_no_consent": audience.blocked_count, "hash": d["hash"][:12],
            "sample_add": [mask(a["email"]) for a in d["add"][:5]], "eligibility": eligibility(sync.provider, d["size_after"]),
            "capabilities": ad.CAPS[sync.provider], "note": ad.NOTES.get(sync.provider)}


async def create_sync(db: AsyncSession, audience: MarketingAudience, acct: AdAccount, user, kind: str = "CUSTOM",
                      origin: Optional[AudienceSync] = None, ratio: Optional[float] = None) -> AudienceSync:
    svc.require_member(user, await svc.control(db, acct))
    if kind == "LOOKALIKE":
        if not ad.CAPS[acct.provider]["lookalike"]:
            raise Refused(422, f"{acct.provider} documents no lookalike API, so none is created. "
                               f"The local similarity score on the audience is not a provider lookalike. {ad.NOTES.get(acct.provider, '')}")
        if origin is None or origin.provider != acct.provider or origin.account_id != acct.id or origin.kind != "CUSTOM":
            raise Refused(422, "A lookalike needs a customer-list seed on the same ad account.")
        if ratio is None or not 0.01 <= ratio <= 0.20:
            raise Refused(422, "Meta lookalike ratio must be between 0.01 and 0.20.")
    name = (f"POVU {audience.name}" if kind == "CUSTOM" else f"POVU {audience.name} lookalike {ratio}")[:200]
    dup = (await db.execute(select(AudienceSync).where(
        AudienceSync.audience_id == audience.id, AudienceSync.account_id == acct.id, AudienceSync.kind == kind,
        AudienceSync.status != "DELETED", AudienceSync.origin_sync_id == (origin.id if origin else None)))).scalars().first()
    if dup is not None and kind == "CUSTOM":
        raise Refused(409, "This audience is already set up on that ad account.")
    s = AudienceSync(audience_id=audience.id, account_id=acct.id, provider=acct.provider, kind=kind, name=name,
                     origin_sync_id=origin.id if origin else None, spec={"ratio": ratio} if ratio else {}, created_by=user.username)
    db.add(s)
    await db.flush()
    _audit(db, user, "audience_sync.created", s.id, {"provider": acct.provider, "kind": kind})
    return s


async def request_approval(db: AsyncSession, sync: AudienceSync, user) -> dict:
    svc.require_member(user, await svc.control(db, await db.get(AdAccount, sync.account_id)))
    if sync.status == "DELETED":
        raise Refused(409, "This audience was deleted.")
    pv = await preview(db, sync)
    if sync.kind == "LOOKALIKE":
        origin = await db.get(AudienceSync, sync.origin_sync_id)
        seeds = len([m for m in (await sent_members(db, origin)).values() if m.state == "IN_SYNC"]) if origin else 0
        if not origin or not origin.external_id or origin.status in ("DELETED", "SIMULATED"):
            raise Refused(409, "The seed list is not on the provider (simulation sends nothing, so no lookalike can be derived).")
        if seeds < ad.MINIMUMS["meta"][0]:
            raise Refused(422, f"Meta needs at least {ad.MINIMUMS['meta'][0]} members in the seed audience; this one has {seeds}.")
    else:
        if pv["add"] == 0 and pv["remove"] == 0:
            raise Refused(409, "Nothing to send: the audience already matches the provider.")
        if pv["eligibility"]["blocking"]:
            raise Refused(422, pv["eligibility"]["note"] + f" Size after sync would be {pv['size_after']}.")
    sync.approval_status, sync.requested_by = "PENDING", user.username
    sync.approval_hash = (await diff(db, sync))["hash"]
    _audit(db, user, "audience_sync.approval_requested", sync.id, {"add": pv["add"], "remove": pv["remove"], "hash": sync.approval_hash[:12]})
    return pv


async def decide(db: AsyncSession, sync: AudienceSync, user, ok: bool) -> None:
    if sync.approval_status != "PENDING":
        raise Refused(409, "Nothing waiting for approval.")
    if user.username in (sync.requested_by, sync.created_by):
        raise Refused(403, "A second person must approve (not the requester or the author).")
    svc.require_member(user, await svc.control(db, await db.get(AdAccount, sync.account_id)))
    if (await diff(db, sync))["hash"] != sync.approval_hash:
        sync.approval_status = "NONE"
        raise Refused(409, "The audience changed after this request (members or consent): ask for approval again.")
    sync.approval_status, sync.approved_by = ("APPROVED" if ok else "REJECTED"), user.username
    _audit(db, user, "audience_sync.decided", sync.id, {"ok": ok, "hash": sync.approval_hash[:12]})


async def _set_members(db: AsyncSession, sync: AudienceSync, rows: list[dict], state: str) -> None:
    have = await sent_members(db, sync)
    for r in rows:
        m = have.get(r["e"])
        if m is None:
            db.add(AudienceSyncMember(sync_id=sync.id, email_sha256=r["e"], phone_sha256=r.get("p"), phone_sha256_np=r.get("pn"), state=state))
        else:
            m.state = state


def _tt_quota(sync: AudienceSync) -> None:
    """TikTok: 24 update operations per audience per rolling 24 h (documented)."""
    now = datetime.now(timezone.utc)
    ops = [t for t in (sync.spec or {}).get("tt_ops", []) if datetime.fromisoformat(t) > now - timedelta(hours=24)]
    if len(ops) >= 24:
        raise Refused(429, "TikTok allows 24 audience updates per rolling 24 hours; try again later.")
    sync.spec = {**(sync.spec or {}), "tt_ops": [*ops, now.isoformat()]}


async def _mode(db: AsyncSession, sync: AudienceSync, acct: AdAccount, ctrl, for_removal: bool = False) -> tuple[str, str]:
    """(mode, transport). Removal (consent withdrawal, delete, reconcile) is never blocked by the export switch: it only
    reduces what the platform holds; but it is only ever a real provider call, never recorded as done without one."""
    g = svc.gate(acct, ctrl) if for_removal else gate(acct, ctrl)
    simulated_id = (sync.external_id or "").startswith("SIM-")
    if for_removal:
        return (sync.mode, "http") if sync.mode == "LIVE" else (g["mode"], g["transport"])
    if sync.mode == "LIVE" and sync.external_id and g["mode"] != "LIVE":
        raise Refused(409, "This audience is live on the provider but live changes are switched off: " + " ".join(g["reasons"]))
    if sync.mode == "SIMULATED" and sync.external_id and not simulated_id and g["mode"] == "LIVE":
        raise Refused(409, "This audience was created in simulation; create a new one for live use.")
    if g["transport"] == "blocked":
        raise Refused(409, " ".join(g["reasons"]))
    return g["mode"], ("offline" if simulated_id else g["transport"])


async def run_sync(db: AsyncSession, sync: AudienceSync, user) -> dict:
    async with svc.root_lock(db, sync):
        await db.refresh(sync)
        out = await _run(db, sync, user)
    await _locked_purge(db, sync)   # a withdrawal that landed while this run held the lock (never leaves IN_SYNC)
    return out


async def _run(db: AsyncSession, sync: AudienceSync, user) -> dict:
    acct = await db.get(AdAccount, sync.account_id)
    ctrl = await svc.control(db, acct)
    svc.require_member(user, ctrl)
    if sync.status == "DELETED":
        raise Refused(409, "This audience was deleted.")
    if sync.status == "UNKNOWN":
        raise Refused(409, "The previous attempt has an unknown outcome: reconcile first (never re-sent blindly).")
    if sync.approval_status != "APPROVED":
        raise Refused(409, "No approved request for this audience.")
    d = await diff(db, sync)
    if d["hash"] != sync.approval_hash:
        sync.approval_status = "NONE"
        raise Refused(409, "Members or consent changed after approval: request approval again.")
    mode, transport = await _mode(db, sync, acct, ctrl)
    sync.mode, sync.status, sync.last_error = mode, "SYNCING", None
    if sync.kind == "LOOKALIKE":
        return await _run_lookalike(db, sync, acct, user, mode, transport)
    if transport != "offline" and sync.provider == "tiktok":
        _tt_quota(sync)
    await _set_members(db, sync, d["add"], "PENDING_ADD")
    have = await sent_members(db, sync)
    for h in d["remove"]:
        have[h].state = "PENDING_REMOVE"
    _audit(db, user, "audience_sync.run", sync.id, {"mode": mode, "transport": transport, "add": len(d["add"]), "remove": len(d["remove"])})
    await db.commit()
    sup = await suppressed(db)      # consent withdrawn since the diff: never sent
    for a in [a for a in d["add"] if a["e"] in sup]:
        have[a["e"]] = (await sent_members(db, sync))[a["e"]]
        have[a["e"]].state = "REMOVED"
    d["add"] = [a for a in d["add"] if a["e"] not in sup]
    rm = [{"e": h, "p": have[h].phone_sha256, "pn": have[h].phone_sha256_np} for h in d["remove"]]
    try:
        if transport == "offline":
            sync.external_id = sync.external_id or f"SIM-AUD-{sync.id.hex[:12]}"
        else:
            if not sync.external_id:
                sync.external_id, _ = await ad.create(sync.provider, acct.external_id, sync.name)
                await db.commit()
            if d["add"]:
                sync.external_id, job = await ad.add(sync.provider, acct.external_id, sync.external_id, d["add"], sync.name)
                sync.last_job_id = job or sync.last_job_id
                await db.commit()
            if rm:
                _, job = await ad.remove(sync.provider, acct.external_id, sync.external_id, rm)
                sync.last_job_id = job or sync.last_job_id
    except (AdsError, EgressBlocked) as e:
        unknown = isinstance(e, AdsError) and e.kind == "UNKNOWN"
        sync.status, sync.last_error = ("UNKNOWN" if unknown else "FAILED"), str(e)[:500]
        await db.commit()
        raise e if isinstance(e, AdsError) else AdsError("PROVIDER", str(e))
    sup = await suppressed(db)      # withdrawn while the provider call ran: not IN_SYNC; the purge below removes them
    await _set_members(db, sync, [a for a in d["add"] if a["e"] not in sup], "IN_SYNC")
    await _set_members(db, sync, [a for a in d["add"] if a["e"] in sup], "PENDING_REMOVE")
    for h in d["remove"]:
        have[h].state = "REMOVED"
    sync.approval_status, sync.last_sync_at = "USED", datetime.now(timezone.utc)
    sync.status = "SIMULATED" if transport == "offline" else "PROCESSING"
    sync.provider_status = "SIMULATED: nothing was sent" if transport == "offline" else "sent, waiting for provider status"
    await db.commit()
    if transport != "offline":
        await poll(db, sync)
    return {"status": sync.status, "mode": sync.mode, "added": len(d["add"]), "removed": len(d["remove"])}


async def _run_lookalike(db, sync: AudienceSync, acct: AdAccount, user, mode: str, transport: str) -> dict:
    origin = await db.get(AudienceSync, sync.origin_sync_id)
    if transport == "offline" or origin is None or not origin.external_id or origin.external_id.startswith("SIM-"):
        sync.status = "DRAFT"
        raise Refused(409, "A provider lookalike needs a seed that exists on the provider; simulation sends nothing and "
                           "no lookalike is invented.")
    try:
        sync.external_id = await ad.lookalike(sync.provider, acct.external_id, sync.name, origin.external_id, float(sync.spec["ratio"]))
    except (AdsError, EgressBlocked) as e:
        unknown = isinstance(e, AdsError) and e.kind == "UNKNOWN"
        sync.status, sync.last_error = ("UNKNOWN" if unknown else "FAILED"), str(e)[:500]
        await db.commit()
        raise e if isinstance(e, AdsError) else AdsError("PROVIDER", str(e))
    sync.approval_status, sync.status, sync.last_sync_at = "USED", "PROCESSING", datetime.now(timezone.utc)
    _audit(db, user, "audience_sync.lookalike", sync.id, {"ratio": sync.spec.get("ratio")})
    await db.commit()
    await poll(db, sync)
    return {"status": sync.status, "mode": sync.mode, "added": 0, "removed": 0}


async def poll(db: AsyncSession, sync: AudienceSync) -> dict:
    """Read the provider's own status. Nothing is READY unless the provider says so."""
    acct = await db.get(AdAccount, sync.account_id)
    if not sync.external_id or sync.status in ("DELETED", "DRAFT"):
        raise Refused(409, "Not on the provider yet.")
    if sync.external_id.startswith("SIM-"):
        sync.provider_status = "SIMULATED: nothing was sent"
        return {"status": sync.status, "provider_status": sync.provider_status}
    try:
        st = await ad.status(sync.provider, acct.external_id, sync.external_id, sync.last_job_id)
    except (AdsError, EgressBlocked) as e:
        sync.last_error = str(e)[:500]
        await db.commit()
        raise e if isinstance(e, AdsError) else AdsError("PROVIDER", str(e))
    sync.status, sync.provider_status, sync.provider_size, sync.last_error = st["state"], st["detail"][:120], st["size"], None
    await db.commit()
    return {"status": sync.status, "provider_status": sync.provider_status, "size": sync.provider_size}


async def reconcile(db: AsyncSession, sync: AudienceSync, user) -> dict:
    """UNKNOWN / FAILED outcome: re-send the pending member operations (add and remove are idempotent at every
    provider), then read the provider status. An unknown *create* is looked up by name first (Meta, LinkedIn)."""
    async with svc.root_lock(db, sync):
        await db.refresh(sync)
        acct = await db.get(AdAccount, sync.account_id)
        ctrl = await svc.control(db, acct)
        svc.require_member(user, ctrl)
        mode, transport = await _mode(db, sync, acct, ctrl, for_removal=True)
        if transport == "offline":
            raise Refused(409, "Simulation sent nothing: there is nothing to reconcile.")
        have = await sent_members(db, sync)
        if not sync.external_id:
            sync.external_id = await ad.find(sync.provider, acct.external_id, sync.name)
            if not sync.external_id:
                sync.status = "FAILED"
                sync.last_error = "Not found on read-back: nothing was created (or the platform has no lookup; check its ads manager)."
                await db.commit()
                return {"status": sync.status, "resent": 0}
        pend_add = [{"e": h, "p": m.phone_sha256, "pn": m.phone_sha256_np} for h, m in have.items() if m.state == "PENDING_ADD"]
        pend_rm = [{"e": h, "p": m.phone_sha256, "pn": m.phone_sha256_np} for h, m in have.items() if m.state == "PENDING_REMOVE"]
        try:
            if pend_add:
                sync.external_id, job = await ad.add(sync.provider, acct.external_id, sync.external_id, pend_add, sync.name)
                sync.last_job_id = job or sync.last_job_id
            if pend_rm:
                await ad.remove(sync.provider, acct.external_id, sync.external_id, pend_rm)
        except (AdsError, EgressBlocked) as e:
            sync.last_error = str(e)[:500]
            await db.commit()
            raise e if isinstance(e, AdsError) else AdsError("PROVIDER", str(e))
        for h, m in have.items():
            m.state = "IN_SYNC" if m.state == "PENDING_ADD" else "REMOVED" if m.state == "PENDING_REMOVE" else m.state
        sync.status = "PROCESSING"
        _audit(db, user, "audience_sync.reconciled", sync.id, {"resent_add": len(pend_add), "resent_remove": len(pend_rm)})
        await db.commit()
        out = await poll(db, sync)
        return {**out, "resent": len(pend_add) + len(pend_rm)}


async def delete_sync(db: AsyncSession, sync: AudienceSync, user) -> None:
    acct = await db.get(AdAccount, sync.account_id)
    ctrl = await svc.control(db, acct)
    svc.require_member(user, ctrl)
    if sync.status == "DELETED":
        return
    if sync.external_id and not sync.external_id.startswith("SIM-"):
        mode, transport = await _mode(db, sync, acct, ctrl, for_removal=True)
        if transport == "offline":
            raise Refused(409, "Cannot reach the provider to delete it: nothing was changed.")
        try:
            await ad.delete(sync.provider, acct.external_id, sync.external_id)
        except (AdsError, EgressBlocked) as e:
            sync.last_error = str(e)[:500]
            await db.commit()
            raise e if isinstance(e, AdsError) else AdsError("PROVIDER", str(e))
    for m in (await sent_members(db, sync)).values():
        m.state = "REMOVED"
    sync.status, sync.provider_status, sync.approval_status = "DELETED", "deleted", "NONE"
    _audit(db, user, "audience_sync.deleted", sync.id, {"provider": sync.provider})


async def suppress_now(db: AsyncSession, email: str) -> Optional[str]:
    """Local, in-transaction half of a consent withdrawal: write the suppression and mark every platform member
    holding this address PENDING_REMOVE. No provider call, so it can sit inside any consent write (unsubscribe link,
    complaint, mail reply, merge). The provider removal runs right after commit (drain) or at the next reconcile."""
    from sqlalchemy.dialects.postgresql import insert
    h = ads.hash_email((email or "").strip().lower())
    if not h:
        return None
    await db.execute(insert(AudienceSuppression).values(email_sha256=h, created_by="consent-change").on_conflict_do_nothing())
    held = (await db.execute(update(AudienceSyncMember).where(AudienceSyncMember.email_sha256 == h, AudienceSyncMember.state.in_(("IN_SYNC", "PENDING_ADD")))
                             .values(state="PENDING_REMOVE"))).rowcount
    await db.flush()
    if held and not db.info.get("m49_drain"):      # no platform holds this person: nothing to drain
        db.info["m49_drain"] = True
        event.listen(db.sync_session, "after_commit", _schedule_drain, once=True)
    return h


_TASKS: set = set()


def _schedule_drain(_session) -> None:
    try:
        t = asyncio.get_running_loop().create_task(drain_removals())
    except RuntimeError:
        return
    _TASKS.add(t)
    t.add_done_callback(_TASKS.discard)


async def drain_removals() -> None:
    """Own session, never raises: provider failure leaves members PENDING_REMOVE (suppressed locally) for Reconcile."""
    from app.db.session import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            syncs = (await db.execute(select(AudienceSync).where(AudienceSync.status != "DELETED", AudienceSync.id.in_(
                select(AudienceSyncMember.sync_id).where(AudienceSyncMember.state == "PENDING_REMOVE"))))).scalars().all()
            for s in syncs:
                await _locked_purge(db, s)
    except Exception:  # noqa: BLE001
        log.exception("audience removal drain failed")


async def _locked_purge(db: AsyncSession, s: AudienceSync, only: Optional[str] = None) -> Optional[list[dict]]:
    """Purge suppressed members of one sync under its run lock (waits briefly: a running sync re-checks on its own)."""
    for _ in range(10):
        cm = svc.root_lock(db, s)
        try:
            await cm.__aenter__()
        except Refused:
            await asyncio.sleep(0.3)
            continue
        try:
            await db.refresh(s)
            res = await _purge(db, s, only)
            await db.commit()
            return res
        finally:
            await cm.__aexit__(None, None, None)
    return None


async def _purge(db: AsyncSession, s: AudienceSync, only: Optional[str] = None) -> list[dict]:
    sup = await suppressed(db)
    todo = [m for m in (await sent_members(db, s)).values() if m.email_sha256 in sup and m.state in SENT
            and (only is None or m.email_sha256 == only)]
    acct, results = await db.get(AdAccount, s.account_id), []
    for m in todo:
        if m.state == "REMOVED":
            continue
        h = m.email_sha256
        r = {"sync_id": str(s.id), "provider": s.provider, "mode": s.mode}
        try:
            if not s.external_id or s.external_id.startswith("SIM-"):
                r["result"] = "REMOVED (simulation: nothing had been sent)"
            else:
                ctrl = await svc.control(db, acct)
                _, transport = await _mode(db, s, acct, ctrl, for_removal=True)
                if transport == "offline":
                    raise AdsError("PROVIDER", "provider is unreachable")
                left = (await db.execute(select(func.count()).select_from(AudienceSyncMember).where(
                    AudienceSyncMember.sync_id == s.id, AudienceSyncMember.state == "IN_SYNC"))).scalar_one() - 1
                if s.provider == "tiktok" and left < ad.MINIMUMS["tiktok"][0]:
                    # TikTok refuses an update that leaves < 1,000: deleting the whole list is the only way to remove them
                    await ad.delete("tiktok", acct.external_id, s.external_id)
                    for x in (await sent_members(db, s)).values():
                        x.state = "REMOVED"
                    s.status, s.provider_status = "DELETED", "deleted to honour a consent withdrawal (list would drop below 1,000)"
                    r["result"] = "AUDIENCE DELETED (TikTok cannot shrink below 1,000)"
                else:
                    await ad.remove(s.provider, acct.external_id, s.external_id, [{"e": h, "p": m.phone_sha256, "pn": m.phone_sha256_np}])
                    r["result"] = "REMOVED"
            m.state = "REMOVED"
        except (AdsError, EgressBlocked) as e:
            m.state = "PENDING_REMOVE"
            r["result"] = f"FAILED: {str(e)[:200]} — stays suppressed locally; use Reconcile to retry"
        results.append(r)
    return results


async def withdraw_consent(db: AsyncSession, user, email: str) -> dict:
    """Consent withdrawn for one e-mail: unsubscribe, suppress for good, remove from every platform list that holds it."""
    email = (email or "").strip().lower()
    h = ads.hash_email(email)
    if not h:
        raise Refused(422, "A valid e-mail address is needed.")
    now = datetime.now(timezone.utc)
    row = (await db.execute(select(CRMContactConsent).where(func.lower(CRMContactConsent.email) == email))).scalar_one_or_none()
    if row is None:
        db.add(CRMContactConsent(email=email, status="UNSUBSCRIBED", source=f"manual:{user.username}", updated_at=now))
    else:
        row.status, row.updated_at = "UNSUBSCRIBED", now
    if await db.get(AudienceSuppression, h) is None:
        db.add(AudienceSuppression(email_sha256=h, created_by=user.username))
    await db.flush()
    held = (await db.execute(select(AudienceSyncMember, AudienceSync).join(AudienceSync, AudienceSync.id == AudienceSyncMember.sync_id)
                             .where(AudienceSyncMember.email_sha256 == h, AudienceSyncMember.state.in_(SENT),
                                    AudienceSync.status != "DELETED"))).all()
    results = []
    for _, s in held:
        res = await _locked_purge(db, s, h)
        results += res if res is not None else [{"sync_id": str(s.id), "provider": s.provider, "mode": s.mode,
                                                 "result": "PENDING: a sync is running; it removes suppressed members itself"}]
    audiences = {s.audience_id for _, s in held} | set((await db.execute(select(MarketingAudienceMember.audience_id).where(
        func.lower(MarketingAudienceMember.email) == email))).scalars())
    for aid in audiences:
        a = await db.get(MarketingAudience, aid)
        if a is not None:
            await aus.recompute(db, a)
    lookalikes = [str(x.id) for x in (await db.execute(select(AudienceSync).where(
        AudienceSync.kind == "LOOKALIKE", AudienceSync.status != "DELETED",
        AudienceSync.origin_sync_id.in_([s.id for _, s in held] or [None])))).scalars()]
    _audit(db, user, "audience_sync.consent_withdrawn", None, {"hash": h[:12], "removed_from": len(results)})
    return {"suppressed": True, "removed": results, "lookalikes_to_review": lookalikes,
            "note": "Provider-generated lookalikes built from a seed that held this person are not changed by removal; review or delete them." if lookalikes else None}


async def conversions_overview(db: AsyncSession) -> list[dict]:
    from app.models.m47_platform import AdsConversionUpload
    rows = (await db.execute(select(AdsConversionUpload.provider, AdsConversionUpload.status, func.count()).group_by(
        AdsConversionUpload.provider, AdsConversionUpload.status))).all()
    return [{"provider": p, "status": s, "count": n} for p, s, n in rows]


def out(s: AudienceSync) -> dict:
    return {"id": str(s.id), "audience_id": str(s.audience_id), "account_id": str(s.account_id), "provider": s.provider,
            "kind": s.kind, "name": s.name, "external_id": s.external_id, "status": s.status, "mode": s.mode,
            "provider_status": s.provider_status, "provider_size": s.provider_size, "approval_status": s.approval_status,
            "requested_by": s.requested_by, "approved_by": s.approved_by, "created_by": s.created_by, "last_error": s.last_error,
            "origin_sync_id": str(s.origin_sync_id) if s.origin_sync_id else None, "spec": {k: v for k, v in (s.spec or {}).items() if k != "tt_ops"},
            "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None}
