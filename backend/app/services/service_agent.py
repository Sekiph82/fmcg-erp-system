"""AI customer service agent for website chat (M45.S01.T007).

Answers come only from (a) approved, public help articles, with numbered citations, and (b) the signed-in portal
customer's own orders and tickets. There is no generative model and no provider fallback: when nothing grounded
applies, the chat goes to a person. It never performs refunds, cancellations, payments or price changes; such requests
are refused and handed to the team. Prompt-injection attempts get a refusal. English and Swahili.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

SW = {"habari", "tafadhali", "asante", "nataka", "agizo", "oda", "bei", "wapi", "lini", "mzigo", "malipo", "bidhaa",
      "hali", "yangu", "jambo", "ninaweza", "je", "naomba", "kwa", "nini", "lakini", "sasa"}
FINANCIAL = re.compile(r"\b(refund|money back|cancel (my |the |an )?order|chargeback|reverse|discount|change (the )?price|"
                       r"credit note|pay me|write.?off|rudisha pesa|kurejesha|punguzo|ghairi)\b", re.I)
ORDER_REF = re.compile(r"\b(SO[-_ ]?[A-Z0-9-]{3,})\b", re.I)
TICKET_REF = re.compile(r"\b(TKT[-_ ]?[A-Z0-9-]{3,}|HD[-_ ]?[A-Z0-9-]{3,})\b", re.I)

T = {
    "en": {"refuse_money": "I can't make refunds, cancellations, payments or price changes. I've passed your request to our team; a person will reply here.",
           "refuse_inject": "I can only help with questions about POVU products, orders and deliveries.",
           "sign_in": "For order or ticket status, please sign in to the customer portal and open the chat from there, so I know it's your account.",
           "not_found": "I couldn't find {ref} on your account. Please check the number, or type 'person' to talk to our team.",
           "order": "Order {ref}: {status}. Ordered {date}; requested delivery {delivery}. Payment: {payment}.",
           "ticket": "Ticket {ref} ({subject}): {status}.",
           "articles": "Here is what our help articles say:",
           "more": "Type 'person' if you still need our team.",
           "handoff": "Thank you, a member of our team will reply here shortly (working hours, Nairobi time)."},
    "sw": {"refuse_money": "Siwezi kurejesha pesa, kughairi oda, kupokea malipo au kubadilisha bei. Ombi lako limepelekwa kwa timu yetu; mtu atakujibu hapa.",
           "refuse_inject": "Ninaweza kusaidia tu kuhusu bidhaa za POVU, oda na usafirishaji.",
           "sign_in": "Kwa hali ya oda au tiketi, tafadhali ingia kwenye portal ya wateja kisha ufungue mazungumzo kutoka hapo.",
           "not_found": "Sikupata {ref} kwenye akaunti yako. Tafadhali angalia namba, au andika 'person' kuongea na timu yetu.",
           "order": "Oda {ref}: {status}. Iliagizwa {date}; usafirishaji ulioombwa {delivery}. Malipo: {payment}.",
           "ticket": "Tiketi {ref} ({subject}): {status}.",
           "articles": "Makala zetu za msaada (kwa Kiingereza) zinasema:",
           "more": "Andika 'person' kama bado unahitaji timu yetu.",
           "handoff": "Asante, mtu kutoka timu yetu atakujibu hapa hivi karibuni (saa za kazi, Nairobi)."},
}


@dataclass
class Reply:
    text: str
    handoff: bool = False
    kind: str = "answer"            # answer | order | ticket | refused | handoff
    citations: list[str] = field(default_factory=list)


def language(text: str) -> str:
    words = set(re.findall(r"[a-z]+", text.lower()))
    return "sw" if len(words & SW) >= 2 or (words & {"habari", "tafadhali", "asante", "oda", "agizo"}) else "en"


async def _portal_customer(db: AsyncSession, sess) -> Optional[uuid.UUID]:
    from app.models.portal import PortalAccount
    if not getattr(sess, "portal_account_id", None):
        return None
    acc = await db.get(PortalAccount, sess.portal_account_id)
    try:
        return uuid.UUID(str(acc.linked_customer_id)) if acc and acc.linked_customer_id else None
    except ValueError:
        return None


async def respond(db: AsyncSession, sess, text: str, handoff_words: re.Pattern) -> Reply:
    from app.core.ai_safety import detect_prompt_injection
    lang = language(text)
    t = T[lang]
    if handoff_words.search(text):
        return Reply(t["handoff"], handoff=True, kind="handoff")
    if detect_prompt_injection(text)["detected"]:
        return Reply(t["refuse_inject"], kind="refused")
    if FINANCIAL.search(text):
        return Reply(t["refuse_money"], handoff=True, kind="refused")
    order, ticket = ORDER_REF.search(text), TICKET_REF.search(text)
    if order or ticket:
        cust = await _portal_customer(db, sess)
        if cust is None:
            return Reply(t["sign_in"], kind="refused")
        if order:
            from app.models.sales import SalesOrder
            ref = order.group(1).upper().replace(" ", "-").replace("_", "-")
            so = (await db.execute(select(SalesOrder).where(func.upper(SalesOrder.order_no) == ref,
                                                            SalesOrder.customer_id == cust))).scalar_one_or_none()
            if so is None:
                return Reply(t["not_found"].format(ref=ref), kind="refused")
            return Reply(t["order"].format(ref=so.order_no, status=so.status.value.lower(), date=so.order_date.isoformat(),
                                           delivery=so.requested_delivery_date.isoformat(),
                                           payment=so.payment_status.value.lower()), kind="order")
        from app.models.helpdesk import HelpdeskTicket
        ref = ticket.group(1).upper().replace(" ", "-").replace("_", "-")
        tk = (await db.execute(select(HelpdeskTicket).where(func.upper(HelpdeskTicket.ticket_no) == ref,
                                                            HelpdeskTicket.customer_id == cust))).scalar_one_or_none()
        if tk is None:
            return Reply(t["not_found"].format(ref=ref), kind="refused")
        return Reply(t["ticket"].format(ref=tk.ticket_no, subject=tk.subject[:80], status=tk.status.value.lower()), kind="ticket")
    from app.services import kb_retrieval
    hits = await kb_retrieval.search(db, text)
    if hits:
        lines = [t["articles"]] + [f"[{i}] {h.title}: {(h.summary or h.body[:200]).strip()} (/kb/{h.slug})"
                                   for i, h in enumerate(hits, 1)]
        return Reply("\n".join(lines + [t["more"]]), citations=[f"/kb/{h.slug}" for h in hits])
    return Reply(t["handoff"], handoff=True, kind="handoff")
