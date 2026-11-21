"""Integration console (M36.S05.T003): one evidence-based health row per connector, mapping health,
retry with exponential backoff and scoped manual sync.

Health is never assumed: a connector is HEALTHY only when its most recent recorded run succeeded;
without credentials it is NOT_CONNECTED; stub connectors are STUB_ONLY; with no recorded run it is NO_DATA.
Secrets are never returned (credential status is set / not set only) and error texts are scrubbed.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.integration_capabilities import (
    IntegrationCapabilityStatus as Cap,
    effective_capability_status,
    list_integration_capabilities,
)
from app.models.integrations import (
    CrmCustomerMapping,
    EcommerceOrderMapping,
    EcommerceProductMapping,
    IntegrationLog,
    IntegrationLogStatus,
    IntegrationProvider,
)

BACKOFF_BASE_SECONDS = 60
BACKOFF_MAX_SECONDS = 6 * 3600
LOG_REF = "console:"  # IntegrationLog.reference prefix for console-run syncs

# capability → (credential store key, IntegrationLog provider used for its runs)
CRED_KEY = {"MPESA_DARAJA": "mpesa", "WHATSAPP": "whatsapp"}
LOG_PROVIDER = {"ECOMMERCE_SYNC": IntegrationProvider.SHOPIFY,
                "CRM_SYNC": IntegrationProvider.CRM, "IOT": IntegrationProvider.IOT,
                "BARCODE_PRINTING": IntegrationProvider.BARCODE}
SYNCABLE = {"EMAIL_SYNC", "ECOMMERCE_SYNC"}

_SECRETISH = re.compile(r"""(?i)(password|passwd|pwd|secret|token|api[_-]?key|passkey|authorization)(["']?\s*(?:[:=]|\bis\b)\s*["']?)(?!\*\*\*)[^\s"',;&}]+""")
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
_URL_CREDS = re.compile(r"(?i)(https?://)[^/\s:@]+:[^/\s@]+@")


def scrub(text: Optional[str]) -> Optional[str]:
    """Error text safe to show: no credential-looking values, no user:pass@ in URLs, bounded length."""
    if not text:
        return None
    text = _BEARER.sub(lambda m: f"{m.group(1)} ***", text)
    text = _URL_CREDS.sub(r"\1***@", text)
    text = _SECRETISH.sub(lambda m: f"{m.group(1)}{m.group(2)}***", text)
    return text[:300]


def backoff_until(consecutive_failures: int, last_failure_at: Optional[datetime]) -> Optional[datetime]:
    """Exponential backoff after failures: 1, 2, 4 … minutes, capped at 6 hours. None when no wait applies."""
    if consecutive_failures <= 0 or last_failure_at is None:
        return None
    wait = min(BACKOFF_BASE_SECONDS * 2 ** (consecutive_failures - 1), BACKOFF_MAX_SECONDS)
    return last_failure_at + timedelta(seconds=wait)


def _ok(status) -> bool:
    return status == IntegrationLogStatus.SUCCESS


async def _runs(db: AsyncSession, key: str) -> list[IntegrationLog]:
    """Most recent recorded runs of a connector (its own provider logs, or console runs for it)."""
    prov = LOG_PROVIDER.get(key)
    cond = IntegrationLog.reference == LOG_REF + key
    if prov is not None:
        cond = cond | (IntegrationLog.provider == prov)
    q = select(IntegrationLog).where(cond, IntegrationLog.status.in_(
        [IntegrationLogStatus.SUCCESS, IntegrationLogStatus.FAILED])).order_by(IntegrationLog.created_at.desc()).limit(20)
    return list((await db.execute(q)).scalars().all())


def _streak(runs: list[IntegrationLog]) -> int:
    n = 0
    for r in runs:
        if _ok(r.status):
            break
        n += 1
    return n


async def _mailboxes(db: AsyncSession) -> dict:
    from app.models.email_integration import EmailAccount
    rows = (await db.execute(select(EmailAccount).where(EmailAccount.is_active.is_(True),
                                                        EmailAccount.imap_host.is_not(None)))).scalars().all()
    return {"connected": len(rows), "with_errors": sum(1 for a in rows if a.sync_error),
            "last_sync_at": max((a.last_sync_at for a in rows if a.last_sync_at), default=None),
            "last_error": scrub(next((a.sync_error for a in rows if a.sync_error), None))}


async def _counts(db: AsyncSession, model, *where) -> dict:
    rows = (await db.execute(select(model.sync_status, func.count()).where(*where).group_by(model.sync_status))).all()
    return {getattr(s, "value", str(s)): n for s, n in rows}


async def _webhooks(db: AsyncSession) -> dict:
    from app.models.webhook import DeliveryAttempt, DeliveryStatus
    rows = (await db.execute(select(DeliveryAttempt.status, func.count()).group_by(DeliveryAttempt.status))).all()
    by = {getattr(s, "value", str(s)): n for s, n in rows}
    nxt = (await db.execute(select(func.min(DeliveryAttempt.next_retry_at)).where(
        DeliveryAttempt.status == DeliveryStatus.RETRYING))).scalar_one()
    return {"by_status": by, "next_retry_at": nxt}


def _configured(key: str, creds: dict, mail: dict) -> Optional[bool]:
    if key in CRED_KEY:
        return creds.get(CRED_KEY[key], False)
    if key == "EMAIL_SYNC":
        return mail["connected"] > 0
    if key == "ECOMMERCE_SYNC":
        from app.services.shopify_service import shopify_configured
        return shopify_configured()
    if key == "ETIMS":
        return bool(settings.ETIMS_CONFIGURED)
    if key == "AI_PROVIDERS":
        return bool(settings.AI_CONFIGURED)
    return None  # built-in / file-based: no credential to set


async def overview(db: AsyncSession) -> dict:
    from app.services.provider_credentials import status as creds_status
    creds = {p["provider"]: p["configured"] for p in await creds_status(db)}
    mail = await _mailboxes(db)
    now = datetime.now(timezone.utc)
    rows = []
    for cap in list_integration_capabilities():
        key = cap.provider
        status = effective_capability_status(cap)
        configured = _configured(key, creds, mail)
        runs = await _runs(db, key)
        last_ok = next((r.created_at for r in runs if _ok(r.status)), None)
        last_fail = next((r for r in runs if not _ok(r.status)), None)
        streak = _streak(runs)
        if key == "EMAIL_SYNC" and streak and not mail["with_errors"] and mail["last_sync_at"] and last_fail \
                and mail["last_sync_at"] > last_fail.created_at:
            streak = 0  # mailboxes synced fine after the failed manual run
        if key == "EMAIL_SYNC" and mail["connected"]:  # the mailbox loop records its result on each account
            last_ok = mail["last_sync_at"] or last_ok
        if status == Cap.STUB_ONLY:
            health = "STUB_ONLY"
        elif status == Cap.SIMULATED_ONLY:
            health = "SIMULATED"  # works only against a simulator: never presented as a live connection
        elif configured is False:
            health = "NOT_CONNECTED"
        elif key == "EMAIL_SYNC" and mail["with_errors"]:
            health = "FAILING"
        elif streak:
            health = "FAILING"
        elif last_ok:
            health = "HEALTHY"
        else:
            health = "NO_DATA"
        retry_at = backoff_until(streak, last_fail.created_at if last_fail else None)
        rows.append({
            "provider": key, "label": cap.label, "capability": status.value, "health": health,
            "credentials": None if configured is None else ("SET" if configured else "NOT_SET"),
            "last_success_at": last_ok, "last_failure_at": last_fail.created_at if last_fail else None,
            "last_error": scrub(mail["last_error"] if key == "EMAIL_SYNC" and mail["with_errors"] else
                                (last_fail.error_message if last_fail and streak else None)),
            "consecutive_failures": streak,
            "next_retry_at": retry_at if retry_at and retry_at > now else None,
            "can_sync": key in SYNCABLE and health not in ("STUB_ONLY", "NOT_CONNECTED"),
            "screen": cap.frontend_route, "notes": cap.notes,
        })
    for name in ("sms", "email"):  # outbound channels kept in the credential store
        label = {"sms": "SMS", "email": "Outgoing e-mail (SMTP)"}[name]
        rows.append({"provider": name.upper() if name == "sms" else "SMTP", "label": label,
                     "capability": "LIVE_READY" if creds.get(name) else "DISABLED",
                     "health": "NO_DATA" if creds.get(name) else "NOT_CONNECTED",
                     "credentials": "SET" if creds.get(name) else "NOT_SET", "last_success_at": None,
                     "last_failure_at": None, "last_error": None, "consecutive_failures": 0, "next_retry_at": None,
                     "can_sync": False, "screen": "/dashboard/integrations/provider-keys", "notes": ""})
    mappings = {
        "crm_customers": await _counts(db, CrmCustomerMapping),
        "ecommerce_orders": await _counts(db, EcommerceOrderMapping),
        "ecommerce_products": await _counts(db, EcommerceProductMapping),
        "mailboxes": {k: v for k, v in mail.items() if k != "last_error"},
        "webhooks": await _webhooks(db),
    }
    return {"connectors": rows, "mappings": mappings, "generated_at": now}


class SyncRefused(Exception):
    def __init__(self, status: int, detail, retry_at: Optional[datetime] = None):
        super().__init__(str(detail))
        self.status, self.detail, self.retry_at = status, detail, retry_at


async def run_sync(db: AsyncSession, key: str, user) -> dict:
    """Manual sync of one connector. Refuses stubs (501), unconnected (409) and runs inside backoff (429).
    Each run is recorded; a run that did nothing is never reported as synced."""
    key = key.upper()
    from sqlalchemy import text as _sql
    if not (await db.execute(_sql("SELECT pg_try_advisory_xact_lock(hashtext(:k))"), {"k": "integration-console:" + key})).scalar_one():
        raise SyncRefused(409, "A sync of this connector is already running.")
    rows = {r["provider"]: r for r in (await overview(db))["connectors"]}
    row = rows.get(key)
    if row is None:
        raise SyncRefused(404, "Unknown connector.")
    if row["health"] == "STUB_ONLY":
        raise SyncRefused(501, {"provider": key, "status": "STUB_ONLY", "detail": "This connector is not implemented; nothing was synchronised."})
    if key not in SYNCABLE:
        raise SyncRefused(409, "This connector has no manual sync; it runs on its own events.")
    if row["health"] == "NOT_CONNECTED":
        raise SyncRefused(409, "Connect this provider first (credentials are not set); nothing was synchronised.")
    if row["next_retry_at"]:
        raise SyncRefused(429, "Waiting before the next retry after failures.", row["next_retry_at"])

    started = datetime.now(timezone.utc)
    prov = LOG_PROVIDER.get(key, IntegrationProvider.GENERIC)
    try:
        if key == "EMAIL_SYNC":
            from app.services.email_mailbox_service import sync_all
            r = await sync_all(db)
            ok = r["failed"] == 0
            result = {"accounts": r["accounts"], "imported": r["imported"], "failed": r["failed"]}
            err = None if ok else f"{r['failed']} mailbox(es) failed; see the mailbox error."
        else:  # ECOMMERCE_SYNC: Shopify order import
            from app.services import shopify_service as shopify
            client = shopify.ShopifyClient.from_settings()
            try:
                res = await shopify.import_orders(db, client, None, user.id, limit=50)
            finally:
                await client.aclose()
            ok = not res.errors and not res.failed  # a partial import is reported as failed, with its errors
            result = {"imported": res.imported, "failed": res.failed}
            err = None if ok else "; ".join(res.errors[:3])
    except Exception as e:  # provider error: record it, never claim success
        await db.rollback()
        ok, result, err = False, {}, f"{type(e).__name__}: {e}"
    from app.services.integration_service import log_call
    await log_call(db, provider=prov, integration_type="SYNC", endpoint=f"console/{key}",
                   response_payload=result or None,
                   status=IntegrationLogStatus.SUCCESS if ok else IntegrationLogStatus.FAILED,
                   error_message=scrub(err), reference=LOG_REF + key,
                   duration_ms=int((datetime.now(timezone.utc) - started).total_seconds() * 1000))
    await db.commit()
    return {"provider": key, "status": "SUCCESS" if ok else "FAILED", "result": result, "error": scrub(err)}
