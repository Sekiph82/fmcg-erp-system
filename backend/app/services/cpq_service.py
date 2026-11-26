"""M45.S01.T014 advanced CPQ and contract lifecycle (the bounded delta on top of what already exists).

Already in place and reused: quote versions (revise), discount approval, share links with view tracking, accept /
decline with signer verification by one-time code, conversion to a sales order, contracts with approval, price lists
with tiers, promotion schemes, subscription order templates, payment links. Added here:
- price book: quote lines priced from the customer's active price list (tiers included);
- promotions on quotes: BUNDLE / MIX_AND_MATCH / TIERED schemes evaluated on the quote and recorded;
- quote templates; optional password on share links;
- multi-step approvals: configurable discount levels, each by a different person holding that level's right, before
  the quote can be sent, accepted or converted;
- quote reporting; readiness check before conversion (credit exposure, stock per line);
- contract from an accepted quote via a contract template; renewal: notice before end, a renewal quote once per
  contract when it auto-renews;
- signature adapters: the built-in evidence flow (LOCAL) is active; DocuSign / Adobe Sign are NOT_CONFIGURED;
- recurring billing: open invoices of subscription orders get a payment link, reminders are retried on a schedule,
  settlement comes from the payment link; the customer portal can open a fresh link for its own invoice;
- credit-note verification against the original invoice (quantities and prices).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cpq import BillingAttempt, ContractRenewal, ContractTemplate, QuoteApproval, QuotePromo, QuoteTemplate

DEFAULTS = {"approval_levels": [{"above_pct": 10, "permission": "sales.approve"}, {"above_pct": 25, "permission": "finance.approve"}],
            "billing_retry_days": [3, 7, 14], "credit_check": True}
SIGNATURE_PROVIDERS = {"LOCAL": "ACTIVE", "DOCUSIGN": "NOT_CONFIGURED", "ADOBE_SIGN": "NOT_CONFIGURED"}


class CPQError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def settings_get(db: AsyncSession) -> dict:
    from app.models.customer_intel import CISetting
    row = await db.get(CISetting, "cpq")
    return {**DEFAULTS, **({k: v for k, v in row.value.items() if k in DEFAULTS} if row else {})}


async def _quote(db: AsyncSession, qid) -> "Quotation":
    from app.models.quotation import Quotation
    q = (await db.execute(select(Quotation).options(selectinload(Quotation.lines)).where(Quotation.id == qid))).scalar_one_or_none()
    if q is None:
        raise CPQError(404, "Quotation not found")
    return q


def recompute(q) -> None:
    sub = Decimal("0")
    tax = Decimal("0")
    for ln in q.lines:
        net = Decimal(ln.qty) * Decimal(ln.unit_price) * (1 - Decimal(ln.discount_pct or 0))
        ln.line_total = (net * (1 + Decimal(ln.tax_rate or 0))).quantize(Decimal("0.0001"))
        sub += net
        tax += net * Decimal(ln.tax_rate or 0)
    sub *= 1 - Decimal(q.discount_pct or 0)
    q.total_amount, q.tax_amount = sub.quantize(Decimal("0.0001")), tax.quantize(Decimal("0.0001"))
    q.grand_total = (sub + tax).quantize(Decimal("0.0001"))


def _editable(q):
    if getattr(q.status, "value", q.status) != "DRAFT":
        raise CPQError(409, "Only a draft quotation can be changed; revise it for a new version.")


# ── price book ───────────────────────────────────────────────────────────────

async def apply_price_book(db: AsyncSession, qid) -> list[dict]:
    from app.schemas.price_list import PriceResolveRequest
    from app.services.price_list_service import resolve_price
    q = await _quote(db, qid)
    _editable(q)
    out = []
    for ln in q.lines:
        if not ln.product_id:
            continue
        r = await resolve_price(db, PriceResolveRequest(product_id=ln.product_id, quantity=Decimal(ln.qty), uom=ln.unit,
                                                        customer_id=q.customer_id, currency=q.currency))
        price = Decimal(str(r.get("unit_price") or 0))
        if price > 0 and r.get("currency", q.currency) == q.currency:
            out.append({"line_no": ln.line_no, "old": str(ln.unit_price), "new": str(price), "source": r.get("resolution_path") or "price list"})
            ln.unit_price = price
        else:
            out.append({"line_no": ln.line_no, "old": str(ln.unit_price), "new": None, "source": "no price in the customer's price book"})
    recompute(q)
    await _refresh_approval(db, q)
    return out


# ── promotions on quotes ─────────────────────────────────────────────────────

async def evaluate_promotions(db: AsyncSession, qid, apply: bool = False) -> dict:
    from app.models.master import Product
    from app.models.sales import Customer
    from app.schemas.promotions import OrderLineInput
    from app.services import promotions_service as promos
    q = await _quote(db, qid)
    cust = await db.get(Customer, q.customer_id)
    lines = []
    for ln in q.lines:
        if not ln.product_id:
            continue
        p = await db.get(Product, ln.product_id)
        lines.append(OrderLineInput(line_id=str(ln.line_no), item_id=ln.product_id, item_category=getattr(getattr(p, "category", None), "value", None),
                                    qty=Decimal(ln.qty), unit_price=Decimal(ln.unit_price), line_total=Decimal(ln.qty) * Decimal(ln.unit_price)))
    res = await promos.evaluate_order(db, q.id, str(q.customer_id), getattr(getattr(cust, "channel", None), "value", None),
                                      getattr(cust, "region", None), None, lines)
    applied = [{"scheme_code": a.scheme_code, "scheme_name": a.scheme_name, "type": getattr(a.application_type, "value", str(a.application_type)),
                "benefit": str(a.calculated_benefit), "lines": [i.model_dump(mode="json") for i in a.line_impacts]} for a in res.applied_promos]
    if apply:
        _editable(q)
        await db.execute(QuotePromo.__table__.delete().where(QuotePromo.quote_id == q.id))
        by_no = {str(ln.line_no): ln for ln in q.lines}
        header = Decimal("0")
        gross = sum((Decimal(ln.qty) * Decimal(ln.unit_price) * (1 - Decimal(ln.discount_pct or 0)) for ln in q.lines), Decimal("0"))
        for a in res.applied_promos:
            db.add(QuotePromo(quote_id=q.id, scheme_code=a.scheme_code, scheme_name=a.scheme_name, benefit=a.calculated_benefit,
                              details=[i.model_dump(mode="json") for i in a.line_impacts]))
            for imp in a.line_impacts:
                ln = by_no.get(str(imp.sales_order_line_id)) if imp.sales_order_line_id else None
                if ln is not None and imp.discount_pct:
                    ln.discount_pct = max(Decimal(ln.discount_pct or 0), Decimal(imp.discount_pct) / 100)
                elif imp.discount_amount:          # scheme-level benefit: carried as a quote-level discount
                    header += Decimal(imp.discount_amount)
        if header and gross > 0:
            q.discount_pct = max(Decimal(q.discount_pct or 0), (header / gross).quantize(Decimal("0.0001")))
        recompute(q)
        await _refresh_approval(db, q)
    return {"applied": applied, "skipped": res.skipped_promos, "total_discount": str(res.total_discount),
            "free_goods_value": str(res.total_free_goods_value)}


# ── templates ────────────────────────────────────────────────────────────────

async def quote_from_template(db: AsyncSession, template_id, customer_id, user_id) -> "Quotation":
    from app.models.quotation import Quotation, QuotationLine, QuoteStatus
    t = await db.get(QuoteTemplate, template_id)
    if t is None:
        raise CPQError(404, "Template not found")
    n = (await db.execute(select(func.count()).select_from(Quotation))).scalar_one()
    q = Quotation(quote_no=f"QT-{date.today():%Y%m%d}-{n + 1:04d}-{uuid.uuid4().hex[:3].upper()}", customer_id=customer_id,
                  status=QuoteStatus.DRAFT, quote_date=date.today(), valid_until=date.today() + timedelta(days=t.valid_days),
                  currency="KES", notes=t.notes, created_by_id=user_id)
    db.add(q)
    await db.flush()
    for i, l in enumerate(t.lines, start=1):
        db.add(QuotationLine(quote_id=q.id, line_no=i, product_id=uuid.UUID(l["product_id"]), qty=Decimal(str(l.get("qty", 1))),
                             unit=l.get("unit", "PCS"), unit_price=Decimal(str(l.get("unit_price", 0))),
                             discount_pct=Decimal(str(l.get("discount_pct", 0))), tax_rate=Decimal(str(l.get("tax_rate", 0.16)))))
    await db.flush()
    await apply_price_book(db, q.id)
    return await _quote(db, q.id)


# ── multi-step approval ──────────────────────────────────────────────────────

async def _refresh_approval(db: AsyncSession, q) -> None:
    """Any price change invalidates earlier level approvals for this version."""
    await db.execute(QuoteApproval.__table__.delete().where(QuoteApproval.quote_id == q.id))


def quote_discount(q) -> Decimal:
    from app.services import discount_approval_service as disc
    return disc.discount_pct(q.lines, Decimal(q.discount_pct or 0) * 100, fraction=True)


async def levels_needed(db: AsyncSession, q) -> list[dict]:
    cfg = await settings_get(db)
    d = quote_discount(q)
    return [dict(l, level=i + 1) for i, l in enumerate(sorted(cfg["approval_levels"], key=lambda x: x["above_pct"])) if d > Decimal(str(l["above_pct"]))]


async def approval_state(db: AsyncSession, q) -> dict:
    need = await levels_needed(db, q)
    done = {a.level: a for a in (await db.execute(select(QuoteApproval).where(QuoteApproval.quote_id == q.id))).scalars()}
    return {"discount_pct": str(quote_discount(q).quantize(Decimal("0.01"))),
            "levels": [{"level": l["level"], "above_pct": l["above_pct"], "permission": l["permission"],
                        "approved_by": done[l["level"]].approver if l["level"] in done else None} for l in need],
            "complete": all(l["level"] in done for l in need)}


async def approve_level(db: AsyncSession, qid, user) -> dict:
    from app.core.access_control import has_permission
    q = await _quote(db, qid)
    st = await approval_state(db, q)
    nxt = next((l for l in st["levels"] if l["approved_by"] is None), None)
    if nxt is None:
        raise CPQError(409, "No approval is waiting for this quotation.")
    if user.id in (q.created_by_id, q.discount_changed_by_id):
        raise CPQError(403, "The person who set the price cannot approve it.")
    if any(a.approver_id == user.id for a in (await db.execute(select(QuoteApproval).where(QuoteApproval.quote_id == q.id))).scalars()):
        raise CPQError(403, "Each level needs a different approver.")
    if not (user.is_superuser or has_permission(user, nxt["permission"])):
        raise CPQError(403, f"Level {nxt['level']} needs {nxt['permission']}.")
    db.add(QuoteApproval(quote_id=q.id, level=nxt["level"], permission=nxt["permission"], approver=user.username, approver_id=user.id,
                         discount_pct=quote_discount(q)))
    await db.flush()
    return await approval_state(db, q)


async def ensure_levels(db: AsyncSession, q, action: str) -> None:
    st = await approval_state(db, q)
    if not st["complete"]:
        missing = [f"level {l['level']} ({l['permission']})" for l in st["levels"] if l["approved_by"] is None]
        raise CPQError(409, f"Approve the {st['discount_pct']}% discount before you {action}: {', '.join(missing)} still open.")


# ── readiness, reporting ─────────────────────────────────────────────────────

async def readiness(db: AsyncSession, qid) -> dict:
    from app.models.inventory import Stock
    from app.models.sales import Customer, Invoice, InvoiceStatus
    q = await _quote(db, qid)
    cust = await db.get(Customer, q.customer_id)
    open_ar = (await db.execute(select(func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0)).where(
        Invoice.customer_id == q.customer_id, Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE])))).scalar_one()
    exposure = Decimal(open_ar) + Decimal(q.grand_total or 0)
    credit = {"limit": str(cust.credit_limit) if cust.credit_limit is not None else None, "open_invoices": str(Decimal(open_ar)),
              "after_order": str(exposure), "ok": cust.credit_limit is None or exposure <= Decimal(cust.credit_limit)}
    stock = []
    for ln in q.lines:
        if not ln.product_id:
            continue
        avail = (await db.execute(select(func.coalesce(func.sum(Stock.quantity_available), 0)).where(
            Stock.product_id == ln.product_id, Stock.is_blocked.is_(False)))).scalar_one()
        stock.append({"line_no": ln.line_no, "needed": str(ln.qty), "available": str(avail), "ok": Decimal(avail) >= Decimal(ln.qty)})
    appr = await approval_state(db, q)
    return {"credit": credit, "stock": stock, "approvals": appr,
            "ready": credit["ok"] and all(s["ok"] for s in stock) and appr["complete"]}


async def report(db: AsyncSession, days: int = 90) -> dict:
    from app.models.quotation import Quotation
    since = date.today() - timedelta(days=days)
    rows = (await db.execute(select(Quotation).options(selectinload(Quotation.lines)).where(Quotation.quote_date >= since))).scalars().all()
    by = {}
    for q in rows:
        st = getattr(q.status, "value", q.status)
        by.setdefault(st, {"count": 0, "value": Decimal("0")})
        by[st]["count"] += 1
        by[st]["value"] += Decimal(q.grand_total or 0)
    won, lost = by.get("ACCEPTED", {}).get("count", 0) + by.get("CONVERTED", {}).get("count", 0), by.get("REJECTED", {}).get("count", 0)
    days_to_accept = [(q.accepted_at.date() - q.quote_date).days for q in rows if q.accepted_at]
    discounts = [quote_discount(q) for q in rows if q.lines]
    return {"period_days": days, "by_status": {k: {"count": v["count"], "value": str(v["value"])} for k, v in by.items()},
            "win_rate": round(won / (won + lost), 3) if won + lost else None,
            "avg_days_to_accept": round(sum(days_to_accept) / len(days_to_accept), 1) if days_to_accept else None,
            "avg_discount_pct": str((sum(discounts) / len(discounts)).quantize(Decimal("0.01"))) if discounts else None}


# ── contracts and renewals ───────────────────────────────────────────────────

def _fill(text: str, q, cust_name: str) -> str:
    return (text.replace("{customer}", cust_name).replace("{quote_no}", q.quote_no)
            .replace("{total}", f"{q.currency} {Decimal(q.grand_total or 0):,.2f}"))


async def contract_from_quote(db: AsyncSession, qid, template_id, user) -> "Contract":
    from app.models.contracts import Contract
    from app.models.sales import Customer
    q = await _quote(db, qid)
    if getattr(q.status, "value", q.status) not in ("ACCEPTED", "CONVERTED"):
        raise CPQError(409, "Only an accepted quotation becomes a contract.")
    t = await db.get(ContractTemplate, template_id)
    if t is None:
        raise CPQError(404, "Contract template not found")
    cust = await db.get(Customer, q.customer_id)
    start = date.today()
    c = Contract(contract_code=f"CT-{start:%Y%m%d}-{uuid.uuid4().hex[:4].upper()}", contract_name=f"{t.name} — {cust.name}"[:200],
                 contract_type=t.contract_type, party_type="CUSTOMER", party_id=q.customer_id, start_date=start,
                 end_date=start + timedelta(days=30 * t.term_months), currency=q.currency[:3], auto_renew=t.auto_renew,
                 renewal_notice_days=t.renewal_notice_days, created_by=user.id,
                 notes=f"From quotation {q.quote_no} v{q.version}\n\n" + "\n\n".join(
                     f"{i}. {cl['title']}\n{_fill(cl['text'], q, cust.name)}" for i, cl in enumerate(t.clauses, start=1)))
    db.add(c)
    await db.flush()
    db.add(ContractRenewal(contract_id=c.id, source_quote_id=q.id))
    await db.flush()
    return c


async def renewals_tick(db: AsyncSession, today: Optional[date] = None) -> int:
    """Notice before a contract ends; for auto-renewing contracts also a renewal quote (once per contract)."""
    from app.models.contracts import Contract
    from app.models.quotation import Quotation, QuotationLine, QuoteStatus
    today = today or date.today()
    n = 0
    rows = (await db.execute(select(ContractRenewal, Contract).join(Contract, Contract.id == ContractRenewal.contract_id).where(
        ContractRenewal.renewal_quote_id.is_(None), Contract.end_date.is_not(None)))).all()
    for r, c in rows:
        if c.end_date - timedelta(days=c.renewal_notice_days or 30) > today or c.status in ("TERMINATED", "ARCHIVED"):
            continue
        r.notified_at = _now()
        if c.auto_renew and r.source_quote_id:
            src = await _quote(db, r.source_quote_id)
            q = Quotation(quote_no=f"{src.quote_no}-R{today:%y}", customer_id=src.customer_id, status=QuoteStatus.DRAFT, quote_date=today,
                          valid_until=c.end_date, currency=src.currency, discount_pct=src.discount_pct,
                          notes=f"Renewal of contract {c.contract_code}", created_by_id=src.created_by_id, crm_record_id=src.crm_record_id)
            db.add(q)
            await db.flush()
            for ln in src.lines:
                db.add(QuotationLine(quote_id=q.id, line_no=ln.line_no, product_id=ln.product_id, description=ln.description, qty=ln.qty,
                                     unit=ln.unit, unit_price=ln.unit_price, discount_pct=ln.discount_pct, tax_rate=ln.tax_rate, line_total=ln.line_total))
            r.renewal_quote_id = q.id
        else:
            r.renewal_quote_id = r.source_quote_id     # notice only: mark handled
        n += 1
    await db.flush()
    return n


# ── recurring billing ────────────────────────────────────────────────────────

async def billing_tick(db: AsyncSession, now: Optional[datetime] = None) -> int:
    """Open invoices of subscription orders: send a payment link, then reminders on the retry schedule."""
    from app.core.config import settings
    from app.models.payments_hub import PaymentLink
    from app.models.sales import Customer, Invoice, InvoiceStatus
    from app.models.subscription import SubscriptionGenerationLog
    from app.services import crm_outbound_service as outbound
    from app.services import payment_link_service as pls
    now = now or _now()
    cfg = await settings_get(db)
    retry = [int(x) for x in cfg["billing_retry_days"]]
    invs = (await db.execute(select(Invoice).join(SubscriptionGenerationLog, SubscriptionGenerationLog.generated_so_id == Invoice.so_id).where(
        Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE])))).scalars().unique().all()
    sent = 0
    for inv in invs:
        b = (await db.execute(select(BillingAttempt).where(BillingAttempt.invoice_id == inv.id).with_for_update())).scalar_one_or_none()
        if b is None:
            b = BillingAttempt(invoice_id=inv.id, status="OPEN", attempts=0)
            db.add(b)
        if b.status != "OPEN":
            continue
        link = await db.get(PaymentLink, b.link_id) if b.link_id else None
        if link is not None and link.status in ("PAID", "TEST_PAID"):
            b.status = "PAID"
            continue
        due = b.last_sent_at is None or (b.attempts <= len(retry) and now >= b.last_sent_at + timedelta(days=retry[min(b.attempts, len(retry)) - 1]))
        if not due:
            continue
        if b.attempts > len(retry):
            b.status = "GAVE_UP"
            continue
        try:
            link, token = await pls.create(db, inv.id, None, 30, True)
        except pls.LinkError:
            b.status = "PAID"
            continue
        b.link_id, b.attempts, b.last_sent_at = link.id, b.attempts + 1, now
        cust = await db.get(Customer, inv.customer_id)
        if cust and cust.email:
            await outbound.queue(db, to_email=cust.email, subject=f"Invoice {inv.invoice_no}" + (" (reminder)" if b.attempts > 1 else ""),
                                 body=f"Your subscription invoice {inv.invoice_no} is ready. Pay by M-Pesa: "
                                      f"{settings.PUBLIC_APP_URL.rstrip('/')}/pay/{token}", purpose="INVOICE",
                                 dedupe_key=f"bill:{inv.id}:{b.attempts}", customer_id=cust.id, created_by="billing")
        sent += 1
    await db.flush()
    return sent


# ── credit notes ─────────────────────────────────────────────────────────────

async def verify_credit_note(db: AsyncSession, return_id) -> dict:
    """Returned quantities and prices must not exceed what was invoiced on the original order (net of earlier returns)."""
    from app.models.returns_mgmt import ReturnLine, ReturnOrder
    from app.models.sales import Invoice, InvoiceLine
    r = await db.get(ReturnOrder, return_id)
    if r is None:
        raise CPQError(404, "Return not found")
    if not r.original_so_id:
        return {"ok": False, "issues": [{"issue": "No original order: the credit cannot be checked against an invoice."}]}
    inv_lines = (await db.execute(select(InvoiceLine).join(Invoice, Invoice.id == InvoiceLine.invoice_id).where(Invoice.so_id == r.original_so_id))).scalars().all()
    invoiced: dict = {}
    for l in inv_lines:
        e = invoiced.setdefault(l.product_id, {"qty": Decimal("0"), "price": Decimal(l.unit_price)})
        e["qty"] += Decimal(l.quantity)
        e["price"] = max(e["price"], Decimal(l.unit_price))
    earlier = dict((await db.execute(select(ReturnLine.product_id, func.sum(ReturnLine.quantity)).join(ReturnOrder, ReturnOrder.id == ReturnLine.return_id)
                                     .where(ReturnOrder.original_so_id == r.original_so_id, ReturnOrder.id != r.id).group_by(ReturnLine.product_id))).all())
    issues = []
    for l in (await db.execute(select(ReturnLine).where(ReturnLine.return_id == r.id))).scalars():
        inv = invoiced.get(l.product_id)
        if inv is None:
            issues.append({"product_id": str(l.product_id), "issue": "not on the original invoice"})
            continue
        left = inv["qty"] - Decimal(earlier.get(l.product_id) or 0)
        if Decimal(l.quantity) > left:
            issues.append({"product_id": str(l.product_id), "issue": f"returned {l.quantity} > invoiced {inv['qty']} minus earlier returns ({left})"})
        if Decimal(l.unit_price) > inv["price"]:
            issues.append({"product_id": str(l.product_id), "issue": f"credit price {l.unit_price} > invoiced price {inv['price']}"})
    return {"ok": not issues, "issues": issues, "credit_note_no": r.credit_note_no}
