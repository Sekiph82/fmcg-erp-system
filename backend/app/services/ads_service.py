"""Ad platform sync and drafts (M44.S01.T002–T005), on top of `ads_adapters`.

- sync(account, since, until): pulls the platform's daily campaign report and upserts it (re-sync replaces a day,
  so the same window twice gives the same numbers). Auth / permission errors mark the account; rate limits keep the
  data and report the retry time.
- Drafts: idempotency key, budget guardrail (ADS_MAX_DAILY_BUDGET in account currency), second-editor approval,
  validation (platform validate-only where documented, otherwise local rules). Publishing is never done here.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

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
