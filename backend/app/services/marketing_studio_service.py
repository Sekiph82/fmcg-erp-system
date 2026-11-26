"""M49.S01.T012 Integrated Marketing Studio: one view over a campaign that LINKS the records other modules own
(approved DAM / brand assets, e-mail designs and campaigns, social posts, ad trees, audiences and audience syncs)
and reads their live state. Nothing is copied or re-implemented: each channel is still submitted and approved in its own
module; the studio shows where it stands.

Analytics are computed only from stored rows. Attribution = ERP sales orders whose campaign_id (or a promotion of the
campaign) points at the campaign, and website-form leads whose utm_campaign equals the campaign code. No other
attribution is inferred; an empty source is reported as "no data", never as zero performance.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.brand_assets import AssetStatus, BrandAsset
from app.models.crm import (AdAccount, CRMEmailCampaign, CRMLeadSubmission, EmailDesign, MarketingAudience, SocialPost)
from app.models.documents import Document, DocumentCategory, DocumentStatus
from app.models.m48_ads import AdCampaignNode
from app.models.m49_audiences import AudienceSync
from app.models.m49_social import SocialPostMetric
from app.models.m49_studio import StudioBudgetRequest, StudioCampaign, StudioLink
from app.models.marketing import AdPerformance, ApprovalStatus, BrandSpend, Campaign, MarketingPromotion
from app.models.sales import SalesOrder, SOLine, SOStatus
from app.services import ads_service as svc

READ = ("marketing.view", "campaigns.view", "marketing.edit", "campaigns.edit", "crm.view_all", "crm.edit_all")
WRITE = ("marketing.edit", "campaigns.edit", "crm.edit_all")
FINANCE = ("finance.approve",)
KINDS = ("DAM_ASSET", "BRAND_ASSET", "EMAIL_DESIGN", "SOCIAL_POST", "AD_TREE", "AUDIENCE_SYNC", "AUDIENCE")
CREATIVE = ("DAM_ASSET", "BRAND_ASSET", "EMAIL_DESIGN")
SUBMITTED = ("SUBMITTING", "SUBMITTED", "PROCESSING", "PUBLISHED", "EXPORTED")
_EXCLUDED = (SOStatus.DRAFT, SOStatus.CANCELLED)


def cap() -> Decimal:
    """MARKETING_STUDIO_BUDGET_CAP (default 50000): the largest campaign budget marketing may set without finance."""
    return Decimal(str(getattr(settings, "MARKETING_STUDIO_BUDGET_CAP", 50000)))


def audit(db: AsyncSession, user, event: str, campaign_id, details: dict) -> None:
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_id=getattr(user, "id", None), actor_email=getattr(user, "email", None),
                    actor_name=getattr(user, "full_name", None), event_type=f"MARKETING_STUDIO_{event}", module="marketing",
                    target_type="marketing_campaign", target_id=str(campaign_id), details=details))


def _asset_state(status: str, latest: bool, version: int, linked: Optional[int], ok_status: tuple) -> dict:
    usable = status in ok_status and latest
    return {"status": status, "version": version, "linked_version": linked, "usable": usable,
            "outdated": (not latest) or (linked is not None and version != linked)}


async def resolve(db: AsyncSession, kind: str, ref: uuid.UUID, user) -> tuple[str, Optional[int]]:
    """Validate that this record may be linked and return (label, version). Raises svc.Refused."""
    if kind == "DAM_ASSET":
        d = await db.get(Document, ref)
        if d is None or d.category != DocumentCategory.MARKETING_CREATIVE:
            raise svc.Refused(404, "Marketing creative asset not found.")
        if d.status != DocumentStatus.APPROVED or not d.is_latest:
            raise svc.Refused(409, "Only the latest APPROVED version of an asset can be linked.")
        return d.title, d.version
    if kind == "BRAND_ASSET":
        a = await db.get(BrandAsset, ref)
        if a is None:
            raise svc.Refused(404, "Brand asset not found.")
        if a.status not in (AssetStatus.APPROVED, AssetStatus.PRINT_READY) or not a.is_latest:
            raise svc.Refused(409, "Only the latest APPROVED brand asset can be linked.")
        return a.name, a.version
    if kind == "EMAIL_DESIGN":
        e = await db.get(EmailDesign, ref)
        if e is None:
            raise svc.Refused(404, "E-mail design not found.")
        if e.status != "PUBLISHED":
            raise svc.Refused(409, "Only a PUBLISHED e-mail design can be linked.")
        return e.name, e.version
    if kind == "SOCIAL_POST":
        p = await db.get(SocialPost, ref)
        if p is None:
            raise svc.Refused(404, "Social post not found.")
        return p.text[:80], p.version
    if kind == "AD_TREE":
        r = await db.get(AdCampaignNode, ref)
        if r is None or r.root_id is not None:
            raise svc.Refused(404, "Ad campaign not found.")
        svc.require_member(user, await svc.control(db, await db.get(AdAccount, r.account_id)))
        return r.name, r.budget_version
    if kind == "AUDIENCE_SYNC":
        s = await db.get(AudienceSync, ref)
        if s is None:
            raise svc.Refused(404, "Audience sync not found.")
        svc.require_member(user, await svc.control(db, await db.get(AdAccount, s.account_id)))
        return s.name, None
    a = await db.get(MarketingAudience, ref)
    if a is None:
        raise svc.Refused(404, "Audience not found.")
    return a.name, None


async def link_view(db: AsyncSession, l: StudioLink) -> dict:
    """The live state of one linked record (what its own module says right now)."""
    base = {"link_id": str(l.id), "kind": l.kind, "ref_id": str(l.ref_id), "label": l.label, "linked_by": l.created_by}
    if l.kind == "DAM_ASSET":
        d = await db.get(Document, l.ref_id)
        st = _asset_state(d.status.value, d.is_latest, d.version, l.linked_version, ("APPROVED",)) if d else None
    elif l.kind == "BRAND_ASSET":
        a = await db.get(BrandAsset, l.ref_id)
        st = _asset_state(a.status.value, a.is_latest, a.version, l.linked_version, ("APPROVED", "PRINT_READY")) if a else None
    elif l.kind == "EMAIL_DESIGN":
        e = await db.get(EmailDesign, l.ref_id)
        newer = e and (await db.scalar(select(func.count()).select_from(EmailDesign).where(
            EmailDesign.family_id == e.family_id, EmailDesign.version > e.version)))
        st = {"status": e.status, "version": e.version, "linked_version": l.linked_version,
              "usable": e.status == "PUBLISHED", "outdated": bool(newer) or e.version != l.linked_version} if e else None
    elif l.kind == "SOCIAL_POST":
        p = await db.get(SocialPost, l.ref_id)
        st = {"status": p.status, "version": p.version, "approved": p.approved_version == p.version, "mode": p.publish_mode,
              "submitted": p.status in SUBMITTED, "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None} if p else None
    elif l.kind == "AD_TREE":
        r = await db.get(AdCampaignNode, l.ref_id)
        st = {"status": r.status, "mode": r.mode, "daily_budget": str(r.daily_budget),
              "submitted": r.status not in ("DRAFT",)} if r else None
    elif l.kind == "AUDIENCE_SYNC":
        s = await db.get(AudienceSync, l.ref_id)
        st = {"status": s.status, "approval": s.approval_status, "mode": s.mode, "provider": s.provider,
              "submitted": s.status not in ("DRAFT",)} if s else None
    else:
        a = await db.get(MarketingAudience, l.ref_id)
        st = {"members": a.member_count, "blocked": a.blocked_count, "consent_required": a.require_consent} if a else None
    return {**base, **(st or {"status": "MISSING", "missing": True})}


async def native(db: AsyncSession, c: Campaign, linked: set) -> list[dict]:
    """Records that already point at the campaign through their own module (no studio link needed)."""
    out = []
    for e in (await db.execute(select(CRMEmailCampaign).where(CRMEmailCampaign.marketing_campaign_id == c.id))).scalars():
        out.append({"kind": "EMAIL_CAMPAIGN", "ref_id": str(e.id), "label": e.name, "status": e.status,
                    "approval": e.approval_status, "audience_size": e.audience_size, "submitted": e.status in ("SCHEDULED", "QUEUED")})
    for p in (await db.execute(select(SocialPost).where(SocialPost.campaign_tag == c.campaign_code))).scalars():
        if p.id not in linked:
            out.append({"kind": "SOCIAL_POST", "ref_id": str(p.id), "label": p.text[:80], "status": p.status,
                        "approved": p.approved_version == p.version, "submitted": p.status in SUBMITTED, "via": "campaign_tag"})
    return out


async def studio(db: AsyncSession, c: Campaign, user) -> dict:
    sc = await db.get(StudioCampaign, c.id)
    links = (await db.execute(select(StudioLink).where(StudioLink.campaign_id == c.id).order_by(StudioLink.created_at))).scalars().all()
    items = [await link_view(db, l) for l in links]
    nat = await native(db, c, {l.ref_id for l in links if l.kind == "SOCIAL_POST"})
    reqs = (await db.execute(select(StudioBudgetRequest).where(StudioBudgetRequest.campaign_id == c.id)
                             .order_by(StudioBudgetRequest.created_at.desc()).limit(20))).scalars().all()
    pending = next((r for r in reqs if r.status == "PENDING"), None)
    brief = (sc.brief if sc else None) or {}
    by = lambda *ks: [i for i in items if i["kind"] in ks and not i.get("missing")]  # noqa: E731
    creative = by(*CREATIVE)
    channels = {
        "email": {"items": by("EMAIL_DESIGN") + [n for n in nat if n["kind"] == "EMAIL_CAMPAIGN"]},
        "social": {"items": by("SOCIAL_POST") + [n for n in nat if n["kind"] == "SOCIAL_POST"]},
        "ads": {"items": by("AD_TREE")},
    }
    for ch in channels.values():
        ch["submitted"] = any(i.get("submitted") for i in ch["items"])
    wanted = brief.get("channels") or []
    ck = [
        ("brief", bool(brief), "Write the brief (summary and key message)."),
        ("creative", any(i["usable"] for i in creative), "Link at least one APPROVED asset or published e-mail design."),
        ("audience", bool(by("AUDIENCE", "AUDIENCE_SYNC")), "Link an audience or an audience sync."),
        ("channels", bool(wanted) and all(channels[w]["items"] for w in wanted if w in channels),
         "Link an item for every channel chosen in the brief." if wanted else "Choose the channels in the brief."),
        ("budget", c.budget is not None and pending is None,
         "A budget request is waiting for finance." if pending else "Set the campaign budget."),
        ("approval", c.approval_status == ApprovalStatus.APPROVED, "The campaign itself is not approved yet."),
    ]
    return {
        "campaign": {"id": str(c.id), "code": c.campaign_code, "name": c.campaign_name, "type": c.campaign_type.value,
                     "status": c.status.value, "approval_status": c.approval_status.value, "objective": c.objective,
                     "start_date": c.start_date.isoformat(), "end_date": c.end_date.isoformat(),
                     "budget": str(c.budget) if c.budget is not None else None},
        "brief": {"data": brief, "version": sc.brief_version if sc else 0, "history": (sc.brief_history if sc else [])[-5:],
                  "updated_by": sc.updated_by if sc else None},
        "creative": creative, "audience": by("AUDIENCE", "AUDIENCE_SYNC"), "channels": channels,
        "missing": [i for i in items if i.get("missing")],
        "budget": {"amount": str(c.budget) if c.budget is not None else None, "cap": str(cap()),
                   "pending": _req(pending) if pending else None, "requests": [_req(r) for r in reqs]},
        "checklist": [{"step": k, "done": bool(d), "reason": None if d else why} for k, d, why in ck],
        "user": {"can_write": user.is_superuser or any(_has(user, p) for p in WRITE),
                 "can_finance_approve": user.is_superuser or any(_has(user, p) for p in FINANCE)},
    }


def _has(user, perm: str) -> bool:
    from app.core.access_control import has_permission
    return has_permission(user, perm)


def _req(r: StudioBudgetRequest) -> dict:
    return {"id": str(r.id), "amount": str(r.amount), "cap": str(r.cap), "status": r.status, "note": r.note,
            "requested_by": r.requested_by, "decided_by": r.decided_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "decided_at": r.decided_at.isoformat() if r.decided_at else None}


async def candidates(db: AsyncSession, c: Campaign, user) -> dict:
    """What can still be linked (approved/usable records only; ad objects only for accounts the user is a member of)."""
    have = {(l.kind, l.ref_id) for l in (await db.execute(select(StudioLink).where(StudioLink.campaign_id == c.id))).scalars()}
    out: dict[str, list] = {k: [] for k in KINDS}

    def add(kind, ref, label, **extra):
        if (kind, ref) not in have:
            out[kind].append({"ref_id": str(ref), "label": label, **extra})

    for d in (await db.execute(select(Document).where(
            Document.category == DocumentCategory.MARKETING_CREATIVE, Document.status == DocumentStatus.APPROVED,
            Document.is_latest.is_(True)).order_by(Document.title).limit(50))).scalars():
        add("DAM_ASSET", d.id, d.title, version=d.version)
    for a in (await db.execute(select(BrandAsset).where(
            BrandAsset.status.in_((AssetStatus.APPROVED, AssetStatus.PRINT_READY)), BrandAsset.is_latest.is_(True))
            .order_by(BrandAsset.name).limit(50))).scalars():
        add("BRAND_ASSET", a.id, a.name, version=a.version)
    for e in (await db.execute(select(EmailDesign).where(EmailDesign.status == "PUBLISHED").order_by(EmailDesign.name).limit(50))).scalars():
        add("EMAIL_DESIGN", e.id, e.name, version=e.version)
    for p in (await db.execute(select(SocialPost).order_by(SocialPost.created_at.desc()).limit(50))).scalars():
        add("SOCIAL_POST", p.id, p.text[:80], status=p.status)
    for a in (await db.execute(select(MarketingAudience).order_by(MarketingAudience.name).limit(50))).scalars():
        add("AUDIENCE", a.id, a.name, members=a.member_count)
    for kind, model, label in (("AD_TREE", AdCampaignNode, None), ("AUDIENCE_SYNC", AudienceSync, None)):
        q = select(model).order_by(model.created_at.desc()).limit(100)
        if kind == "AD_TREE":
            q = q.where(AdCampaignNode.root_id.is_(None))
        for r in (await db.execute(q)).scalars():
            try:
                svc.require_member(user, await svc.control(db, await db.get(AdAccount, r.account_id)))
            except svc.Refused:
                continue
            add(kind, r.id, r.name, status=r.status)
    return out


async def analytics(db: AsyncSession, c: Campaign, company_id: Optional[uuid.UUID] = None) -> dict:
    """Channel analytics and ERP attribution, from stored rows only."""
    promo_ids = select(MarketingPromotion.id).where(MarketingPromotion.campaign_id == c.id)
    oq = (select(SalesOrder.id, SalesOrder.currency, func.sum(SOLine.ordered_quantity * SOLine.unit_price * (1 - SOLine.discount_pct)))
          .join(SOLine, SOLine.so_id == SalesOrder.id)
          .where(or_(SalesOrder.campaign_id == c.id, SalesOrder.promotion_id.in_(promo_ids)), SalesOrder.status.not_in(_EXCLUDED))
          .group_by(SalesOrder.id, SalesOrder.currency))
    if company_id:
        oq = oq.where(SalesOrder.company_id == company_id)
    rev: dict[str, Decimal] = defaultdict(Decimal)
    n_orders = 0
    for _, ccy, val in (await db.execute(oq)).all():
        n_orders += 1
        rev[ccy] += Decimal(val or 0)

    leads: dict[str, int] = defaultdict(int)
    src_col = func.lower(func.coalesce(CRMLeadSubmission.utm_source, "unknown")).label("src")
    for src, n in (await db.execute(select(src_col, func.count())
                                    .where(func.lower(CRMLeadSubmission.utm_campaign) == c.campaign_code.lower())
                                    .group_by(src_col))).all():
        leads[src] = n

    ads: dict[str, dict] = {}
    for plat, imp, clk, sp, conv, rows in (await db.execute(
            select(AdPerformance.platform, func.sum(AdPerformance.impressions), func.sum(AdPerformance.clicks),
                   func.sum(AdPerformance.spend), func.sum(AdPerformance.conversions), func.count())
            .where(AdPerformance.campaign_id == c.id).group_by(AdPerformance.platform))).all():
        ads[plat.value] = {"rows": rows, "impressions": int(imp or 0), "clicks": int(clk or 0), "conversions": int(conv or 0),
                           "spend": str(sp or 0)}

    post_ids = select(StudioLink.ref_id).where(StudioLink.campaign_id == c.id, StudioLink.kind == "SOCIAL_POST")
    tagged = select(SocialPost.id).where(SocialPost.campaign_tag == c.campaign_code)
    social: dict[str, dict] = defaultdict(dict)
    for net, metric, val in (await db.execute(
            select(SocialPostMetric.network, SocialPostMetric.metric, func.sum(SocialPostMetric.value))
            .where(or_(SocialPostMetric.post_id.in_(post_ids), SocialPostMetric.post_id.in_(tagged)))
            .group_by(SocialPostMetric.network, SocialPostMetric.metric))).all():
        social[net][metric] = str(val)

    spend: dict[str, Decimal] = defaultdict(Decimal)
    for ccy, amt in (await db.execute(select(BrandSpend.currency, func.sum(BrandSpend.amount)).where(
            BrandSpend.campaign_id == c.id, BrandSpend.approval_status == ApprovalStatus.APPROVED).group_by(BrandSpend.currency))).all():
        spend[ccy] += Decimal(amt or 0)
    roas = {k: str((rev[k] / spend[k]).quantize(Decimal("0.01"))) for k in spend if spend[k] > 0 and k in rev}

    return {
        "campaign_id": str(c.id), "campaign_code": c.campaign_code, "company_id": str(company_id) if company_id else None,
        "attribution": {"orders": n_orders, "revenue": {k: str(v.quantize(Decimal("0.01"))) for k, v in sorted(rev.items())},
                        "leads": sum(leads.values()), "leads_by_source": dict(sorted(leads.items())),
                        "has_data": bool(n_orders or leads),
                        "basis": ["Orders: sales orders whose campaign (or a promotion of this campaign) is set; confirmed orders only "
                                  "(not draft or cancelled); revenue net of tax; per currency, never summed across currencies.",
                                  "Leads: website-form submissions whose utm_campaign equals the campaign code.",
                                  "Nothing else is attributed; people are never matched by e-mail or phone."]},
        "channels": {"ads": {"has_data": bool(ads), "by_platform": ads},
                     "social": {"has_data": bool(social), "by_network": social},
                     "email": {"has_data": False, "note": "Per-campaign e-mail engagement is not stored; see the e-mail campaign itself."}},
        "spend": {"approved_brand_spend": {k: str(v) for k, v in sorted(spend.items())}, "roas": roas,
                  "note": "ROAS = attributed revenue / approved brand spend, same currency only."},
        "no_data": not (n_orders or leads or ads or social),
    }
