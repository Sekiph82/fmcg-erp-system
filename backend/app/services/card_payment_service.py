"""M48.S01.T010 card payments on customer payment links: Pesapal API 3.0 hosted checkout (Kenya; Visa/Mastercard,
also M-Pesa/Airtel on the same page).

Official contract (Pesapal API 3.0 JSON, read 2026-11-26):
  https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/api-reference
  https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/registeripnurl
  https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/submitorderrequest
  https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/gettransactionstatus
  https://developer.pesapal.com/how-to-integrate/e-commerce/api-30-json/refund-request
Base URLs: sandbox https://cybqa.pesapal.com/pesapalv3, live https://pay.pesapal.com/v3.
  POST /api/Auth/RequestToken {consumer_key, consumer_secret} -> {token, expiryDate, error, status} (token ~5 min)
  POST /api/URLSetup/RegisterIPN {url, ipn_notification_type GET|POST} -> {ipn_id, ...}
  POST /api/Transactions/SubmitOrderRequest {id, currency, amount, description, callback_url, notification_id,
       billing_address{email_address|phone_number, ...}} -> {order_tracking_id, merchant_reference, redirect_url}
  GET  /api/Transactions/GetTransactionStatus?orderTrackingId= -> {status_code 0 INVALID|1 COMPLETED|2 FAILED|
       3 REVERSED, payment_status_description, confirmation_code, amount, currency, merchant_reference, ...}
  POST /api/Transactions/RefundRequest {confirmation_code, amount, username, remarks} -> {status "200", message};
       one refund per payment; "200" means received, not effected (it shows later as REVERSED).
  IPN: Pesapal calls our URL with OrderTrackingId, OrderNotificationType=IPNCHANGE, OrderMerchantReference and expects
       {orderNotificationType, orderTrackingId, orderMerchantReference, status 200}. IPNs are NOT signed, so an IPN is
       only a hint: we re-query GetTransactionStatus and trust that answer alone.

Rules here: the card number/CVV never touch us (hosted page only); every call goes through provider_client (egress
guard); the consumer secret is sealed at rest; money is real only with environment=LIVE + CARD_PAYMENTS_LIVE_ENABLED +
two finance people (request + approve). Sandbox/simulator payments are TEST_SETTLED and never reach collections or the
ledger. A real COMPLETED payment becomes one PENDING collection (unique per tracking id, claimed under a row lock) that
finance confirms into the ledger through the existing collections flow — never booked twice, never bypassing finance.
"""
from __future__ import annotations

import asyncio
import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Protocol

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.provider_http import EgressBlocked, _is_local_host, egress_mode, provider_client
from app.models.m48_payments import CardPayment, CardProviderConfig, CardRefund
from app.models.payments_hub import PaymentLink

SANDBOX_BASE = "https://cybqa.pesapal.com/pesapalv3"
LIVE_BASE = "https://pay.pesapal.com/v3"
CURRENCIES = {"KES", "USD"}                # what a Kenyan Pesapal merchant account settles
CARD_PENDING_TTL = timedelta(minutes=30)   # an unpaid hosted checkout stops reserving the balance after this
REQUERY_MIN_GAP = timedelta(seconds=5)     # IPN/return replays inside this window do not re-query the provider
STATES = {0: "INVALID", 1: "COMPLETED", 2: "FAILED", 3: "REVERSED"}


class CardError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


class ProviderUnknown(CardError):
    """Transport failure after retries: the provider may or may not have acted."""
    def __init__(self, msg: str):
        super().__init__(502, msg)


class _Unauthorized(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── provider interface + Pesapal adapter ─────────────────────────────────────

class PaymentProvider(Protocol):
    name: str

    async def create_order(self, *, reference: str, amount: Decimal, currency: str, description: str,
                           callback_url: str, email: Optional[str], phone: Optional[str], name: str) -> dict: ...
    async def status(self, tracking_id: str) -> dict: ...
    async def refund(self, *, confirmation_code: str, amount: Decimal, username: str, remarks: str) -> tuple[bool, str]: ...


_tokens: dict[tuple[str, str, str], tuple[str, datetime]] = {}


def _perr(data: dict) -> str:
    e = data.get("error") or {}
    return (e.get("message") or e.get("code") or data.get("message") or "provider error")[:200] if isinstance(e, dict) else str(e)[:200]


class Pesapal:
    name = "PESAPAL"

    def __init__(self, base_url: str, key: str, secret: str, ipn_id: Optional[str] = None):
        self.base, self.key, self.secret, self.ipn_id = base_url.rstrip("/"), key, secret, ipn_id

    async def _send(self, client: httpx.AsyncClient, method: str, path: str, *, token: Optional[str] = None,
                    retry: bool, **kw) -> dict:
        tries = 3 if retry else 1
        for i in range(tries):
            try:
                r = await client.request(method, self.base + path, headers={
                    "Accept": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})}, **kw)
            except EgressBlocked as e:
                raise CardError(503, str(e)) from None
            except httpx.TransportError as e:
                if i == tries - 1:
                    raise ProviderUnknown(f"No answer from Pesapal ({type(e).__name__}).") from None
                await asyncio.sleep(0.2 * 2 ** i)
                continue
            if r.status_code == 401:
                raise _Unauthorized()
            if r.status_code >= 500 and i < tries - 1:
                await asyncio.sleep(0.2 * 2 ** i)
                continue
            if r.status_code >= 400:
                raise CardError(502, f"Pesapal answered HTTP {r.status_code}.")
            try:
                return r.json()
            except ValueError:
                raise CardError(502, "Pesapal answered with something that is not JSON.") from None
        raise ProviderUnknown("No answer from Pesapal.")

    async def _token(self, client: httpx.AsyncClient, fresh: bool = False) -> str:
        k = (self.base, self.key, hashlib.sha256(self.secret.encode()).hexdigest())   # new secret, new token
        hit = _tokens.get(k)
        if hit and not fresh and hit[1] > _now() + timedelta(seconds=30):
            return hit[0]
        data = await self._send(client, "POST", "/api/Auth/RequestToken", retry=True,
                                json={"consumer_key": self.key, "consumer_secret": self.secret})
        if not data.get("token"):
            raise CardError(502, f"Pesapal refused the credentials: {_perr(data)}")
        try:
            exp = datetime.fromisoformat(str(data.get("expiryDate")).replace("Z", "+00:00"))
            exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        except ValueError:
            exp = _now() + timedelta(minutes=4)
        _tokens[k] = (data["token"], min(exp, _now() + timedelta(minutes=5)))
        return data["token"]

    async def _call(self, method: str, path: str, *, retry: bool, **kw) -> dict:
        async with provider_client() as client:
            for fresh in (False, True):            # one retry with a new token if the cached one was refused
                try:
                    return await self._send(client, method, path, token=await self._token(client, fresh), retry=retry, **kw)
                except _Unauthorized:
                    if fresh:
                        raise CardError(502, "Pesapal refused our access token.") from None
        raise CardError(502, "unreachable")

    async def register_ipn(self, url: str) -> str:
        data = await self._call("POST", "/api/URLSetup/RegisterIPN", retry=False,
                                json={"url": url, "ipn_notification_type": "GET"})
        if not data.get("ipn_id"):
            raise CardError(502, f"Pesapal did not register the notification URL: {_perr(data)}")
        return data["ipn_id"]

    async def create_order(self, *, reference, amount, currency, description, callback_url, email, phone, name) -> dict:
        first, _, last = (name or "Customer").partition(" ")
        body = {"id": reference, "currency": currency, "amount": float(amount), "description": description[:100],
                "callback_url": callback_url, "notification_id": self.ipn_id,
                "billing_address": {"email_address": email or "", "phone_number": phone or "", "country_code": "KE",
                                    "first_name": first[:50], "last_name": last[:50]}}
        data = await self._call("POST", "/api/Transactions/SubmitOrderRequest", retry=False, json=body)  # not idempotent
        if str(data.get("status")) != "200" or not data.get("order_tracking_id") or not data.get("redirect_url"):
            raise CardError(502, f"Pesapal did not accept the order: {_perr(data)}")
        return {"tracking_id": data["order_tracking_id"], "redirect_url": data["redirect_url"]}

    async def status(self, tracking_id: str) -> dict:
        data = await self._call("GET", "/api/Transactions/GetTransactionStatus", retry=True,
                                params={"orderTrackingId": tracking_id})
        if str(data.get("status")) != "200" or data.get("status_code") is None:
            raise CardError(502, f"Pesapal status query failed: {_perr(data)}")
        code = int(data["status_code"])
        return {"state": STATES.get(code, "INVALID"), "code": code,
                "description": str(data.get("payment_status_description") or "")[:200],
                "confirmation_code": data.get("confirmation_code") or None,
                "method": (data.get("payment_method") or None) and str(data["payment_method"])[:40],
                "amount": Decimal(str(data.get("amount") or 0)).quantize(Decimal("0.01")),
                "currency": str(data.get("currency") or "").upper(),
                "merchant_reference": data.get("merchant_reference")}

    async def refund(self, *, confirmation_code, amount, username, remarks) -> tuple[bool, str]:
        data = await self._call("POST", "/api/Transactions/RefundRequest", retry=False, json={
            "confirmation_code": confirmation_code, "amount": f"{Decimal(amount):.2f}", "username": username[:100],
            "remarks": remarks[:255]})
        return str(data.get("status")) == "200", str(data.get("message") or _perr(data))[:255]


# ── configuration, activation ────────────────────────────────────────────────

def _live_flag() -> bool:
    return bool(getattr(settings, "CARD_PAYMENTS_LIVE_ENABLED", False))


async def config(db: AsyncSession, lock: bool = False) -> Optional[CardProviderConfig]:
    q = select(CardProviderConfig).where(CardProviderConfig.provider == "PESAPAL")
    if lock:
        q = q.with_for_update().execution_options(populate_existing=True)
    return (await db.execute(q)).scalar_one_or_none()


def is_live(cfg: Optional[CardProviderConfig]) -> bool:
    return bool(cfg and cfg.environment == "LIVE" and cfg.live_active and _live_flag())


def mode(cfg: Optional[CardProviderConfig]) -> str:
    if cfg is None or not cfg.ipn_id:
        return "NOT_CONFIGURED"
    return "LIVE" if is_live(cfg) else "SIMULATED"


def disabled_reasons(cfg: Optional[CardProviderConfig]) -> list[str]:
    if cfg is None:
        return ["No Pesapal credentials saved yet."]
    out = []
    if not cfg.ipn_id:
        out.append("The payment-notification (IPN) URL is not registered with Pesapal yet.")
    if cfg.environment != "LIVE":
        out.append("Sandbox credentials: card payments are test payments and never reach the ledger.")
    else:
        if not _live_flag():
            out.append("Live card payments are switched off on this server (CARD_PAYMENTS_LIVE_ENABLED).")
        if not cfg.live_active:
            out.append("Live card payments need a second finance approver." if cfg.live_requested_by_id
                       else "Live card payments have not been requested for approval.")
    return out


def provider(cfg: CardProviderConfig) -> Pesapal:
    from app.services.webhook_service import _read_webhook_secret
    return Pesapal(cfg.base_url, cfg.consumer_key, _read_webhook_secret(cfg.consumer_secret_stored) or "", cfg.ipn_id)


def view(cfg: Optional[CardProviderConfig]) -> dict:
    return {"provider": "PESAPAL", "mode": mode(cfg), "disabled_reasons": disabled_reasons(cfg),
            "environment": cfg.environment if cfg else None, "base_url": cfg.base_url if cfg else None,
            "consumer_key_set": bool(cfg and cfg.consumer_key), "ipn_registered": bool(cfg and cfg.ipn_id),
            "ipn_url": cfg.ipn_url if cfg else None, "live_requested": bool(cfg and cfg.live_requested_by_id),
            "live_active": bool(cfg and cfg.live_active), "live_flag": _live_flag()}


async def save_config(db: AsyncSession, user, environment: str, consumer_key: str, consumer_secret: str,
                      base_url: Optional[str] = None) -> CardProviderConfig:
    from urllib.parse import urlsplit
    from app.services.webhook_service import _store_webhook_secret
    if environment not in ("SANDBOX", "LIVE"):
        raise CardError(422, "Environment must be SANDBOX or LIVE.")
    official = SANDBOX_BASE if environment == "SANDBOX" else LIVE_BASE
    if base_url and base_url.rstrip("/") != official:
        if egress_mode() == "live" or not _is_local_host(urlsplit(base_url).hostname or ""):
            raise CardError(422, f"Only the official Pesapal address ({official}) or a local simulator is allowed.")
    cfg = await config(db, lock=True)
    if cfg is None:
        cfg = CardProviderConfig(provider="PESAPAL")
        db.add(cfg)
    cfg.environment, cfg.base_url = environment, (base_url or official).rstrip("/")
    cfg.consumer_key, cfg.consumer_secret_stored = consumer_key.strip(), _store_webhook_secret(consumer_secret.strip())
    cfg.ipn_id = cfg.ipn_url = None                        # new credentials: register the IPN again
    cfg.live_active, cfg.live_requested_by_id, cfg.live_approved_by_id = False, None, None
    cfg.updated_by_id = user.id
    _audit(db, user, "CARD_PROVIDER_SAVED", "card_provider", "PESAPAL", {"environment": environment})
    await db.flush()
    return cfg


async def register_ipn(db: AsyncSession, user) -> CardProviderConfig:
    cfg = await config(db, lock=True)
    if cfg is None:
        raise CardError(409, "Save the Pesapal credentials first.")
    url = f"{settings.PUBLIC_API_URL.rstrip('/')}/api/v1/public/card-ipn/pesapal"
    cfg.ipn_id, cfg.ipn_url = await provider(cfg).register_ipn(url), url
    _audit(db, user, "CARD_IPN_REGISTERED", "card_provider", "PESAPAL", {"ipn_url": url})
    return cfg


async def request_live(db: AsyncSession, user) -> CardProviderConfig:
    cfg = await config(db, lock=True)
    if cfg is None or cfg.environment != "LIVE" or not cfg.ipn_id:
        raise CardError(409, "Save LIVE credentials and register the IPN URL first.")
    if not _live_flag():
        raise CardError(409, "Live card payments are switched off on this server (CARD_PAYMENTS_LIVE_ENABLED).")
    cfg.live_requested_by_id, cfg.live_active = user.id, False
    _audit(db, user, "CARD_LIVE_REQUESTED", "card_provider", "PESAPAL", {})
    return cfg


async def approve_live(db: AsyncSession, user) -> CardProviderConfig:
    cfg = await config(db, lock=True)
    if cfg is None or not cfg.live_requested_by_id:
        raise CardError(409, "Nobody has requested live card payments.")
    if cfg.live_requested_by_id == user.id:
        raise CardError(403, "You requested live card payments; another finance approver must approve.")
    cfg.live_approved_by_id, cfg.live_active = user.id, True
    _audit(db, user, "CARD_LIVE_APPROVED", "card_provider", "PESAPAL", {})
    return cfg


def _audit(db: AsyncSession, user, event: str, target_type: str, target_id: Optional[str], details: dict) -> None:
    from app.models.audit_log import AuditLog
    db.add(AuditLog(actor_id=getattr(user, "id", None), actor_email=getattr(user, "email", None),
                    actor_name=getattr(user, "full_name", None), event_type=event, module="finance",
                    target_type=target_type, target_id=target_id, details=details))


# ── checkout ─────────────────────────────────────────────────────────────────

async def start_checkout(db: AsyncSession, link: PaymentLink, amount: Optional[Decimal], email: Optional[str],
                         phone: Optional[str], user=None) -> CardPayment:
    """`link` must be locked by the caller (SELECT … FOR UPDATE). Returns the payment with the hosted redirect_url."""
    from app.models.sales import Customer, Invoice
    from app.services.payment_link_service import open_balance
    if link.revoked_at is not None or link.status != "ACTIVE":
        raise CardError(409, "This payment link is not open for payment.")
    if link.expires_at <= _now():
        raise CardError(410, "This payment link has expired.")
    cfg = await config(db)
    if mode(cfg) == "NOT_CONFIGURED":
        raise CardError(503, "Card payments are not set up: " + " ".join(disabled_reasons(cfg)))
    inv = await db.get(Invoice, link.invoice_id, with_for_update=True, populate_existing=True)
    if link.currency != inv.currency:
        raise CardError(422, f"Currency mismatch: link {link.currency}, invoice {inv.currency}. Create a new link.")
    if inv.currency not in CURRENCIES:
        raise CardError(422, f"Card payments take {', '.join(sorted(CURRENCIES))} only.")
    recent = (await db.execute(select(func.count()).select_from(CardPayment).where(
        CardPayment.link_id == link.id, CardPayment.created_at >= _now() - timedelta(hours=1)))).scalar_one()
    if recent >= 5:
        raise CardError(429, "Too many card attempts on this link; try again in an hour.")
    due = await open_balance(db, inv)
    amount = due if amount is None else Decimal(amount)
    if amount != amount.quantize(Decimal("0.01")):
        raise CardError(422, "Enter the amount with at most two decimals.")
    if amount <= 0 or amount > due:
        raise CardError(422, f"Enter an amount between 0.01 and {due}.")
    if amount < due and not link.allow_partial:
        raise CardError(422, "This link only accepts the full amount.")
    cust = await db.get(Customer, inv.customer_id)
    email, phone = email or (cust.email if cust else None), phone or (cust.phone if cust else None)
    if not email and not phone:
        raise CardError(422, "Pesapal needs the payer's e-mail or phone number.")
    p = CardPayment(link_id=link.id, invoice_id=inv.id, simulated=not is_live(cfg), amount=amount, currency=inv.currency,
                    merchant_reference=f"POVU-{inv.invoice_no}-{secrets.token_hex(4).upper()}"[-50:],
                    created_by_id=getattr(user, "id", None))
    db.add(p)
    await db.flush()
    try:
        o = await provider(cfg).create_order(
            reference=p.merchant_reference, amount=amount, currency=p.currency,
            description=f"POVU invoice {inv.invoice_no}", email=email, phone=phone, name=cust.name if cust else "",
            callback_url=f"{settings.PUBLIC_API_URL.rstrip('/')}/api/v1/public/card-ipn/return")
    except CardError as e:
        # no redirect URL reached the payer, so nothing can be paid on this order; it reserves nothing
        p.status, p.status_description = "FAILED", f"Not started: {e}"[:200]
        raise
    p.order_tracking_id, p.redirect_url = o["tracking_id"], o["redirect_url"]
    if user is not None:
        _audit(db, user, "CARD_CHECKOUT_CREATED", "invoice", str(inv.id), {"payment": str(p.id), "amount": str(amount)})
    return p


# ── status, settlement (exactly once), reversal ──────────────────────────────

async def _lock(db: AsyncSession, model, id_):
    return (await db.execute(select(model).where(model.id == id_).with_for_update()
                             .execution_options(populate_existing=True))).scalar_one_or_none()


async def refresh(db: AsyncSession, payment_id, *, notified: bool = False, force: bool = False) -> CardPayment:
    """Ask the provider and apply its answer. Concurrent IPNs/replays serialise on the payment row; inside
    REQUERY_MIN_GAP a replay is answered from what we already know."""
    p = await _lock(db, CardPayment, payment_id)
    if p is None:
        raise CardError(404, "Card payment not found.")
    if notified:
        p.notifications += 1
    if not p.order_tracking_id:
        return p
    if not force and p.last_checked_at and _now() - p.last_checked_at < REQUERY_MIN_GAP:
        return p
    cfg = await config(db)
    if cfg is None:
        raise CardError(503, "Card payments are not set up.")
    s = await provider(cfg).status(p.order_tracking_id)
    p.last_checked_at, p.status_description = _now(), s["description"] or s["state"]
    if s["merchant_reference"] and s["merchant_reference"] != p.merchant_reference:
        p.status_description = "Provider returned another order's reference: finance review."
        if p.settlement == "NONE":
            p.settlement = "NEEDS_REVIEW"
        return p
    if s["state"] == "COMPLETED":
        if p.status != "COMPLETED":
            p.status, p.completed_at = "COMPLETED", _now()
            p.confirmation_code, p.payment_method = s["confirmation_code"], s["method"]
        if (s["amount"], s["currency"]) != (Decimal(p.amount), p.currency):
            if p.settlement == "NONE":
                p.settlement = "NEEDS_REVIEW"
                p.status_description = f"Provider reports {s['amount']} {s['currency']}, order was {p.amount} {p.currency}."
        else:
            await _settle(db, p)
    elif s["state"] == "FAILED":
        if p.status in ("PENDING", "EXPIRED", "INVALID"):
            p.status = "FAILED"
    elif s["state"] == "REVERSED":
        if p.status != "REVERSED":
            p.status = "REVERSED"
            await _reverse(db, p)
    elif p.status == "PENDING" and p.created_at < _now() - CARD_PENDING_TTL:
        p.status = "INVALID"                             # never paid; a later COMPLETED still settles (money moved)
    return p


async def _settle(db: AsyncSession, p: CardPayment) -> None:
    from app.api.v1.endpoints.field_app import open_to_collect
    from app.models.field_ops import CashCollection
    from app.models.sales import Invoice
    if p.settlement != "NONE":                            # the ledger claim: only the first verified answer books
        return
    link = await _lock(db, PaymentLink, p.link_id)
    inv = await db.get(Invoice, p.invoice_id, with_for_update=True, populate_existing=True)
    amount = Decimal(p.amount)
    if p.simulated:
        p.settlement = "TEST_SETTLED"                     # sandbox money: never a collection, never "paid"
        link.settled_amount = Decimal(link.settled_amount) + amount
        if link.status == "ACTIVE" and link.settled_amount >= Decimal(inv.total_amount) - Decimal(inv.paid_amount):
            link.status = "TEST_PAID"
        return
    if amount > await open_to_collect(db, inv):
        p.settlement = "NEEDS_REVIEW"
        p.status_description = "Paid after the balance was covered: refund or credit the customer."
        return
    c = CashCollection(collection_no=f"COL-CARD-{secrets.token_hex(5).upper()}", customer_id=inv.customer_id,
                       invoice_id=inv.id, sales_order_id=inv.so_id, collection_date=date.today(), method="BANK_TRANSFER",
                       amount=amount, currency=p.currency, reference=f"Card {p.provider} {p.confirmation_code or ''}"[:100],
                       status="PENDING", client_ref=f"card:{p.order_tracking_id}"[:64],
                       notes=f"Card payment via {p.provider} hosted checkout (tracking {p.order_tracking_id}). "
                             "Finance confirms when it reaches the bank.")
    db.add(c)
    await db.flush()
    p.settlement, p.collection_id = "COLLECTION", c.id
    link.settled_amount = Decimal(link.settled_amount) + amount
    if link.status == "ACTIVE" and await open_to_collect(db, inv) <= 0:
        link.status = "PAID"


async def _reverse(db: AsyncSession, p: CardPayment) -> None:
    """The provider reports the payment REVERSED (our approved refund, or a reversal we did not ask for)."""
    from app.models.field_ops import CashCollection
    from app.models.sales import Invoice, InvoiceStatus
    refund = (await db.execute(select(CardRefund).where(CardRefund.card_payment_id == p.id).with_for_update())).scalar_one_or_none()
    amount = Decimal(refund.amount) if refund is not None and refund.status in ("SUBMITTED", "UNKNOWN") else Decimal(p.amount)
    link = await _lock(db, PaymentLink, p.link_id)
    if p.settlement in ("TEST_SETTLED", "COLLECTION"):
        link.settled_amount = max(Decimal("0"), Decimal(link.settled_amount) - amount)
        if link.status in ("PAID", "TEST_PAID") and link.expires_at > _now():
            link.status = "ACTIVE"
    if p.settlement == "COLLECTION":
        c = await _lock(db, CashCollection, p.collection_id)
        if c is not None and c.status in ("PENDING", "DEPOSITED"):           # never booked: shrink or cancel it
            if amount >= Decimal(c.amount):
                c.status = "CANCELLED"
            else:
                c.amount = Decimal(c.amount) - amount
        elif c is not None and c.status in ("CONFIRMED", "RECONCILED"):      # booked: book the refund, reopen AR
            from app.services import sales_service as ss
            inv = await db.get(Invoice, p.invoice_id, with_for_update=True, populate_existing=True)
            rule = await ss._active_posting_rule(db, "CUSTOMER_PAYMENT_RECEIVED_BANK")
            if rule is not None:
                je = await ss._post_sales_journal(
                    db, source_event="CUSTOMER_CARD_REFUND", source_id=p.id, source_ref=p.confirmation_code or str(p.id),
                    entry_date=date.today(), description=f"Card refund for invoice {inv.invoice_no}", amount=amount,
                    currency=inv.currency, user_id=refund.approved_by_id if refund else None,
                    debit_lines=[(rule.credit_account_id, amount, f"Receivable reopened by card refund {p.confirmation_code}")],
                    credit_lines=[(rule.clearing_account_id, amount, f"Card refund {p.confirmation_code}")])
                if refund is not None:
                    refund.journal_entry_id = je.id
            inv.paid_amount = max(Decimal("0"), Decimal(inv.paid_amount) - amount)
            inv.status = (InvoiceStatus.PARTIALLY_PAID if inv.paid_amount > 0 else
                          InvoiceStatus.OVERDUE if inv.due_date < date.today() else InvoiceStatus.ISSUED)
    if refund is not None and refund.status in ("SUBMITTED", "UNKNOWN"):
        refund.status, refund.decided_at = "COMPLETED", refund.decided_at or _now()
        if amount >= Decimal(p.amount):
            p.settlement = "REFUNDED"
    else:
        p.status_description = "Reversed at the provider without a refund from us: finance review."
        if p.settlement == "NONE":
            p.settlement = "NEEDS_REVIEW"
        else:
            p.settlement = "REFUNDED"


async def expire_stale(db: AsyncSession, now: Optional[datetime] = None) -> int:
    from sqlalchemy import update
    now = now or _now()
    res = await db.execute(update(CardPayment).where(CardPayment.status == "PENDING",
                                                     CardPayment.created_at < now - CARD_PENDING_TTL).values(status="EXPIRED"))
    return res.rowcount or 0


async def pending_reserved(db: AsyncSession, invoice_id) -> Decimal:
    v = (await db.execute(select(func.coalesce(func.sum(CardPayment.amount), 0)).where(
        CardPayment.invoice_id == invoice_id, CardPayment.status == "PENDING", CardPayment.order_tracking_id.is_not(None),
        CardPayment.created_at >= _now() - CARD_PENDING_TTL))).scalar_one()
    return Decimal(v)


# ── refunds (two people) ─────────────────────────────────────────────────────

async def request_refund(db: AsyncSession, user, payment_id, amount: Decimal, reason: str) -> CardRefund:
    p = await _lock(db, CardPayment, payment_id)
    if p is None:
        raise CardError(404, "Card payment not found.")
    if p.status != "COMPLETED" or not p.confirmation_code:
        raise CardError(409, "Only a completed card payment with a provider confirmation code can be refunded.")
    if (await db.execute(select(CardRefund.id).where(CardRefund.card_payment_id == p.id))).first():
        raise CardError(409, "Pesapal allows one refund per payment, and this payment already has one.")
    amount = Decimal(amount)
    if amount <= 0 or amount > Decimal(p.amount) or amount != amount.quantize(Decimal("0.01")):
        raise CardError(422, f"Refund between 0.01 and {p.amount}.")
    r = CardRefund(card_payment_id=p.id, amount=amount, reason=reason.strip()[:255], requested_by_id=user.id)
    db.add(r)
    await db.flush()
    _audit(db, user, "CARD_REFUND_REQUESTED", "card_payment", str(p.id), {"refund": str(r.id), "amount": str(amount)})
    return r


async def decide_refund(db: AsyncSession, user, refund_id, approve: bool) -> CardRefund:
    r = await _lock(db, CardRefund, refund_id)
    if r is None:
        raise CardError(404, "Refund not found.")
    if r.status != "REQUESTED":
        raise CardError(409, f"Refund is {r.status}.")
    if r.requested_by_id == user.id:
        raise CardError(403, "You requested this refund; another finance approver must decide.")
    r.approved_by_id, r.decided_at = user.id, _now()
    if not approve:
        r.status = "REJECTED"
        _audit(db, user, "CARD_REFUND_REJECTED", "card_refund", str(r.id), {})
        return r
    p = await _lock(db, CardPayment, r.card_payment_id)
    cfg = await config(db)
    if cfg is None:
        raise CardError(503, "Card payments are not set up.")
    try:
        ok, msg = await provider(cfg).refund(confirmation_code=p.confirmation_code, amount=r.amount,
                                             username=user.email or str(user.id), remarks=r.reason)
        r.status, r.provider_message = ("SUBMITTED" if ok else "FAILED"), msg
    except ProviderUnknown as e:
        r.status, r.provider_message = "UNKNOWN", f"{e} Refresh the payment status to see whether it was reversed."
    _audit(db, user, "CARD_REFUND_APPROVED", "card_refund", str(r.id), {"status": r.status})
    return r


# ── reconciliation view (with the customer's credit position) ────────────────

async def reconciliation(db: AsyncSession, invoice_id) -> dict:
    from app.models.field_ops import CashCollection
    from app.models.sales import Customer, Invoice
    from app.services.sales_service import _get_customer_outstanding
    inv = await db.get(Invoice, invoice_id)
    if inv is None:
        raise CardError(404, "Invoice not found")
    cust = await db.get(Customer, inv.customer_id)
    outstanding = await _get_customer_outstanding(db, inv.customer_id)
    rows = (await db.execute(select(CardPayment).where(CardPayment.invoice_id == inv.id)
                             .order_by(CardPayment.created_at.desc()))).scalars().all()
    refunds = {r.card_payment_id: r for r in (await db.execute(select(CardRefund).where(
        CardRefund.card_payment_id.in_([p.id for p in rows] or [None])))).scalars()}
    cols = {c.id: c for c in (await db.execute(select(CashCollection).where(
        CashCollection.id.in_([p.collection_id for p in rows if p.collection_id] or [None])))).scalars()}
    out = []
    for p in rows:
        c, r = cols.get(p.collection_id), refunds.get(p.id)
        out.append({"id": str(p.id), "amount": str(p.amount), "currency": p.currency, "status": p.status,
                    "status_description": p.status_description, "settlement": p.settlement, "simulated": p.simulated,
                    "redirect_url": p.redirect_url if p.status == "PENDING" else None,
                    "tracking_id": p.order_tracking_id, "confirmation_code": p.confirmation_code,
                    "payment_method": p.payment_method, "notifications": p.notifications,
                    "collection": {"id": str(c.id), "no": c.collection_no, "status": c.status,
                                   "amount": str(c.amount), "posted": c.payment_id is not None} if c else None,
                    "refund": {"id": str(r.id), "amount": str(r.amount), "status": r.status, "reason": r.reason,
                               "message": r.provider_message, "requested_by": str(r.requested_by_id),
                               "journal_entry_id": str(r.journal_entry_id) if r.journal_entry_id else None} if r else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None})
    limit = Decimal(cust.credit_limit) if cust and cust.credit_limit is not None else None
    return {"invoice_id": str(inv.id), "invoice_no": inv.invoice_no, "currency": inv.currency,
            "total": str(inv.total_amount), "paid": str(inv.paid_amount), "status": inv.status.value,
            "credit": {"limit": str(limit) if limit is not None else None, "outstanding": str(outstanding),
                       "available": str(max(limit - outstanding, Decimal("0"))) if limit is not None else None,
                       "over_limit": bool(limit is not None and outstanding > limit),
                       "note": "Card money frees credit only after finance confirms it into the ledger."},
            "card_payments": out}
