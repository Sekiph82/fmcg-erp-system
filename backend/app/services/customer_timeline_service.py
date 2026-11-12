"""M36.S03.T002 unified customer timeline: one newest-first view over the native records that touch a
customer — CRM records and activities, interactions, visits, calls, meetings, quotes, orders, invoices,
payments, field visits, support tickets and linked e-mail threads. Read-only; every source keeps its
own permission. Each source's event time is the column it is ordered and paged by, so the cursor is
applied in SQL and long histories page without gaps."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any, Callable, Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import can_view_record, get_effective_permission_codes
from app.models.crm import CRMActivity, CRMRecord
from app.models.email_integration import EmailAccount, EmailThread
from app.models.field_sales import VisitLog
from app.models.helpdesk import HelpdeskTicket
from app.models.marketing import CRMProfile, CustomerInteraction, CustomerVisit
from app.models.meetings import MeetingRecord
from app.models.quotation import Quotation
from app.models.sales import Invoice, Payment, SalesOrder
from app.models.voip import CallLog

FAR_FUTURE = datetime(9999, 1, 1, tzinfo=timezone.utc)


def _at(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time.min, timezone.utc)
    return None


def _v(value: Any) -> Any:
    return getattr(value, "value", value)


def can_see(user: Any, module: str) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    codes = set(get_effective_permission_codes(user))
    return "*" in codes or any(c == f"{module}.view" or c.startswith(f"{module}.view_") for c in codes)


@dataclass
class Source:
    kind: str
    group: str                      # permission group reported in hidden_sources
    module: str                     # view permission module ("" = owner-scoped e-mail)
    time_col: Any                   # event time == ordering == paging column
    query: Callable[[UUID, Any], Any]
    render: Callable[[Any], dict]


def _render(kind, title, status=None, ref=None, link=None, detail=None):
    return {"kind": kind, "title": title, "status": _v(status), "ref": ref, "link": link,
            "detail": (detail or None) and str(detail)[:300]}


def _email_query(cid, user):
    q = select(EmailThread).where(EmailThread.linked_object_id == cid)
    if not getattr(user, "is_superuser", False):  # mailboxes are personal
        q = q.where(EmailThread.account_id.in_(select(EmailAccount.id).where(EmailAccount.created_by_id == user.id)))
    return q


# Calls, meetings and interactions are CRM touch-points; the helpdesk UI is gated by quality.view.
SOURCES = [
    Source("crm_record", "crm", "crm", CRMRecord.created_at,
           lambda cid, u: select(CRMRecord).where(CRMRecord.assigned_customer_id == cid),
           lambda r: _render("crm_record", f"{_v(r.record_type).title()} created: {r.company_name}", r.status,
                             r.opportunity_code or r.lead_code, f"/dashboard/crm/records/{r.id}")),
    Source("crm_activity", "crm", "crm", CRMActivity.created_at,
           lambda cid, u: select(CRMActivity).join(CRMRecord, CRMRecord.id == CRMActivity.crm_record_id)
           .where(CRMRecord.assigned_customer_id == cid),
           lambda a: _render("crm_activity", f"{_v(a.activity_type)}: {a.subject}", a.result_status, None,
                             f"/dashboard/crm/records/{a.crm_record_id}", a.notes)),
    Source("interaction", "interactions", "crm", CustomerInteraction.interaction_date,
           lambda cid, u: select(CustomerInteraction).join(CRMProfile, CRMProfile.id == CustomerInteraction.crm_profile_id)
           .where(CRMProfile.customer_id == cid),
           lambda r: _render("interaction", f"Interaction ({r.channel or 'other'})", detail=r.summary)),
    Source("visit", "interactions", "crm", CustomerVisit.visit_date,
           lambda cid, u: select(CustomerVisit).where(CustomerVisit.customer_id == cid),
           lambda v: _render("visit", "Marketing visit", detail=_v(v.outcome))),
    Source("call", "calls_meetings", "crm", CallLog.created_at,
           lambda cid, u: select(CallLog).where(CallLog.customer_id == cid),
           lambda c: _render("call", f"{(c.direction or 'call').title()} call", c.outcome, c.call_ref, "/dashboard/calls", c.notes)),
    Source("meeting", "calls_meetings", "crm", MeetingRecord.scheduled_at,
           lambda cid, u: select(MeetingRecord).where(MeetingRecord.customer_id == cid),
           lambda m: _render("meeting", f"Meeting: {m.title}", m.status, detail=m.outcome)),
    Source("quote", "sales", "sales", Quotation.quote_date,
           lambda cid, u: select(Quotation).where(Quotation.customer_id == cid),
           lambda q: _render("quote", f"Quotation {q.quote_no}", q.status, q.quote_no, "/dashboard/sales/quotes")),
    Source("order", "sales", "sales", SalesOrder.order_date,
           lambda cid, u: select(SalesOrder).where(SalesOrder.customer_id == cid),
           lambda o: _render("order", f"Sales order {o.order_no}", o.status, o.order_no, f"/dashboard/sales/orders/{o.id}")),
    Source("invoice", "sales", "sales", Invoice.invoice_date,
           lambda cid, u: select(Invoice).where(Invoice.customer_id == cid),
           lambda i: _render("invoice", f"Invoice {i.invoice_no}", i.status, i.invoice_no, f"/dashboard/sales/invoices/{i.id}")),
    Source("payment", "sales", "sales", Payment.payment_date,
           lambda cid, u: select(Payment).join(Invoice, Invoice.id == Payment.invoice_id).where(Invoice.customer_id == cid),
           lambda p: _render("payment", f"Payment {p.amount}", ref=p.reference, link=f"/dashboard/sales/invoices/{p.invoice_id}")),
    Source("field_visit", "sales", "sales", VisitLog.visit_date,
           lambda cid, u: select(VisitLog).where(VisitLog.customer_id == cid),
           lambda v: _render("field_visit", "Field sales visit", detail=_v(v.outcome))),
    Source("ticket", "tickets", "quality", HelpdeskTicket.created_at,
           lambda cid, u: select(HelpdeskTicket).where(HelpdeskTicket.customer_id == cid),
           lambda t: _render("ticket", f"Ticket {t.ticket_no}: {t.subject}", t.status, t.ticket_no, "/dashboard/helpdesk")),
    Source("email", "email", "", EmailThread.last_message_at, _email_query,
           lambda t: _render("email", f"E-mail: {t.subject}", link="/dashboard/communication", detail=t.snippet)),
]


def _bound(col, moment: datetime):
    """The cursor in the column's own type (date, naive UTC or aware timestamp)."""
    col_type = col.property.columns[0].type if hasattr(col, "property") else col.type
    if isinstance(col_type, Date) and not isinstance(col_type, DateTime):
        return moment.date()
    if isinstance(col_type, DateTime) and not col_type.timezone:
        return moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment


async def timeline(db: AsyncSession, customer_id: UUID, user: Any, limit: int = 50,
                   before: Optional[str] = None, types: Optional[set[str]] = None) -> dict:
    """Newest-first page of events. `before` is the `next` cursor of the previous page ("<iso>|<key>")."""
    before_at, before_key = FAR_FUTURE, "~"
    if before:
        at_text, _, before_key = before.partition("|")
        before_at = _at(datetime.fromisoformat(at_text))
        if before_at is None or not before_key:
            raise ValueError("bad cursor")
    events, hidden = [], set()
    for src in SOURCES:
        if types and src.kind not in types:
            continue
        if src.module and not can_see(user, src.module):
            hidden.add(src.group)
            continue
        q = src.query(customer_id, user).where(src.time_col.isnot(None))
        if before:
            q = q.where(src.time_col <= _bound(src.time_col, before_at))
        # rows sharing the cursor's timestamp are re-read and filtered by key below
        rows = (await db.execute(q.order_by(src.time_col.desc()).limit(limit + 50))).scalars().all()
        for row in rows:
            # record-level scope too: another rep's order or opportunity stays hidden from scoped users
            if src.module and not can_view_record(user, src.module, row):
                continue
            at = _at(getattr(row, src.time_col.key))
            key = f"{src.kind}:{row.id}"
            if at is not None and (at, key) < (before_at, before_key):
                events.append({"key": key, "type": src.kind, "at": at.isoformat(),
                               **{k: v for k, v in src.render(row).items() if k != "kind"}})
    events.sort(key=lambda e: (e["at"], e["key"]), reverse=True)
    page = events[:limit]
    nxt = f"{page[-1]['at']}|{page[-1]['key']}" if len(events) > limit else None
    return {"events": page, "next": nxt, "hidden_sources": sorted(hidden)}
