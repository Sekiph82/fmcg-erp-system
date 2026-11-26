"""
WhatsApp Business API Integration
──────────────────────────────────
Prefix: /api/v1/whatsapp

Routes:
  GET  /configs              – list WA configs
  POST /configs              – add WA config
  POST /send/text            – send text message
  POST /send/template        – send template message
  POST /webhook              – Meta/Twilio webhook (no auth)
  GET  /webhook              – Meta webhook verification
  GET  /messages             – message log with filters
  POST /simulate-inbound     – demo: create fake inbound message
  GET  /templates            – list templates
  POST /templates            – create template
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Literal, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from app.core.callback_security import verify_meta_signature
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.whatsapp import (
    WhatsAppConfig, WhatsAppConsent, WhatsAppMessage, WhatsAppTemplate,
    WAMessageDirection, WAMessageType, WAMessageStatus,
)
from pydantic import BaseModel, Field
from app.schemas.whatsapp import (
    WAConfigCreate, WAConfigRead, WAConfigUpdate,
    WASendText, WASendTemplate,
    WAMessageRead,
    WATemplateCreate, WATemplateRead,
    WASimulateInbound,
)

_META_GRAPH_URL = "https://graph.facebook.com/v19.0"


async def _meta_send_text(
    phone_number_id: str, api_token: str, to: str, body: str
) -> Tuple[Optional[str], Optional[str]]:
    """Call Meta Cloud API for a text message. Returns (external_msg_id, error_message)."""
    url = f"{_META_GRAPH_URL}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+"),
        "type": "text",
        "text": {"body": body},
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url, json=payload,
                headers={"Authorization": f"Bearer {api_token}"},
            )
        data = resp.json()
        if resp.is_success:
            msg_id = (data.get("messages") or [{}])[0].get("id")
            return msg_id, None
        error = data.get("error", {}).get("message", resp.text[:300])
        return None, error
    except httpx.RequestError as exc:
        return None, f"Network error: {exc}"


async def _meta_send_template(
    phone_number_id: str, api_token: str, to: str,
    template_name: str, language: str, variables: List[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Call Meta Cloud API for a template message. Returns (external_msg_id, error_message)."""
    url = f"{_META_GRAPH_URL}/{phone_number_id}/messages"
    template: dict[str, Any] = {"name": template_name, "language": {"code": language}}
    if variables:
        template["components"] = [
            {"type": "body", "parameters": [{"type": "text", "text": v} for v in variables]}
        ]
    payload = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+"),
        "type": "template",
        "template": template,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url, json=payload,
                headers={"Authorization": f"Bearer {api_token}"},
            )
        data = resp.json()
        if resp.is_success:
            msg_id = (data.get("messages") or [{}])[0].get("id")
            return msg_id, None
        error = data.get("error", {}).get("message", resp.text[:300])
        return None, error
    except httpx.RequestError as exc:
        return None, f"Network error: {exc}"

router = APIRouter()


# ── Opt-in / opt-out ──────────────────────────────────────────────────────────
# Exact keywords (case-insensitive) that opt a phone out; the value is the language of the one-time acknowledgement.
STOP_WORDS = {"STOP": "en", "UNSUBSCRIBE": "en", "ACHA": "sw", "DUR": "tr"}
START_WORDS = {"START", "ANZA", "BAŞLA", "BASLA"}
STOP_ACK = {
    "en": "You will no longer receive WhatsApp messages from us. Reply START to opt back in.",
    "sw": "Hutapokea tena ujumbe wa WhatsApp kutoka kwetu. Jibu ANZA ukitaka kupokea tena.",
    "tr": "Artık bizden WhatsApp mesajı almayacaksınız. Tekrar almak için BAŞLA yazın.",
}
SERVICE_WINDOW = timedelta(hours=24)   # Meta: replies are allowed for 24 h after the customer's last message


def norm_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return f"+{digits}" if digits else ""


async def _consent(db: AsyncSession, phone: str) -> Optional[WhatsAppConsent]:
    return (await db.execute(select(WhatsAppConsent).where(WhatsAppConsent.phone == norm_phone(phone)))).scalar_one_or_none()


async def _set_consent(db: AsyncSession, phone: str, status: str, source: str,
                       text: Optional[str] = None, user_id: Optional[uuid.UUID] = None) -> Optional[str]:
    """Record the latest consent event for a phone; returns the previous status (None if new). Caller commits."""
    from sqlalchemy.dialects.postgresql import insert
    p, now = norm_phone(phone), datetime.now(timezone.utc)
    inserted = (await db.execute(insert(WhatsAppConsent).values(
        id=uuid.uuid4(), phone=p, status=status, source=source[:100], consent_text=text, recorded_by_id=user_id, updated_at=now,
    ).on_conflict_do_nothing(index_elements=["phone"]))).rowcount == 1
    if inserted:
        return None
    row = (await db.execute(select(WhatsAppConsent).where(WhatsAppConsent.phone == p).with_for_update())).scalar_one()
    prev = row.status
    row.status, row.source, row.updated_at, row.recorded_by_id = status, source[:100], now, user_id
    if text:
        row.consent_text = text
    await db.flush()
    return prev


async def send_blocked_reason(db: AsyncSession, phone: str) -> Optional[str]:
    """None when an outbound message to this phone is allowed: not opted out, and either opted in or inside the
    24-hour window after the customer's own last message."""
    p = norm_phone(phone)
    if not p:
        return "the phone number is empty"
    c = await _consent(db, p)
    if c is not None and c.status == "OPTED_OUT":
        return f"{p} has opted out of WhatsApp messages"
    if c is not None and c.status == "OPTED_IN":
        return None
    recent = (await db.execute(select(WhatsAppMessage.id).where(
        WhatsAppMessage.phone == p, WhatsAppMessage.direction == WAMessageDirection.INBOUND,
        WhatsAppMessage.created_at >= datetime.now(timezone.utc) - SERVICE_WINDOW).limit(1))).first()
    return None if recent else f"no WhatsApp opt-in is recorded for {p}"


async def _require_may_send(db: AsyncSession, phone: str) -> None:
    reason = await send_blocked_reason(db, phone)
    if reason:
        raise HTTPException(422, f"Not sent: {reason}.")


async def _handle_keywords(db: AsyncSession, config: WhatsAppConfig, phone: str, body: Optional[str]) -> None:
    """STOP / UNSUBSCRIBE / ACHA / DUR opt the phone out and are acknowledged once; START / ANZA / BAŞLA opt back in."""
    word = (body or "").strip().upper()
    if word in STOP_WORDS:
        if await _set_consent(db, phone, "OPTED_OUT", f"inbound:{word}") != "OPTED_OUT":
            await _deliver_ack(db, config, norm_phone(phone), STOP_ACK[STOP_WORDS[word]])
    elif word in START_WORDS:
        await _set_consent(db, phone, "OPTED_IN", f"inbound:{word}", text=body)


async def _deliver_ack(db: AsyncSession, config: WhatsAppConfig, phone: str, text: str) -> None:
    if config.is_demo_mode:
        external_id, error_msg, status = f"demo_{uuid.uuid4().hex[:12]}", None, WAMessageStatus.DELIVERED
    elif config.api_token and config.business_phone_id:
        external_id, error_msg = await _meta_send_text(config.business_phone_id, config.api_token, phone, text)
        status = WAMessageStatus.SENT if external_id else WAMessageStatus.FAILED
    else:
        external_id, error_msg, status = None, "Live mode requires api_token and business_phone_id", WAMessageStatus.FAILED
    db.add(WhatsAppMessage(config_id=config.id, direction=WAMessageDirection.OUTBOUND, message_type=WAMessageType.TEXT,
                           status=status, phone=phone, body=text, external_msg_id=external_id, error_message=error_msg,
                           linked_module="whatsapp_consent"))


class WAConsentIn(BaseModel):
    phone: str = Field(..., min_length=5, max_length=20)
    status: Literal["OPTED_IN", "OPTED_OUT"]
    proof: Optional[str] = Field(None, max_length=2000)   # how/when the customer agreed (required for OPTED_IN)


@router.get("/consents/{phone}")
async def get_consent(phone: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    c = await _consent(db, phone)
    return {"phone": norm_phone(phone), "status": c.status if c else "NONE", "source": c.source if c else None,
            "updated_at": c.updated_at.isoformat() if c else None, "blocked_reason": await send_blocked_reason(db, phone)}


@router.post("/consents")
async def record_consent(body: WAConsentIn, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Staff record a customer's opt-in (with proof) or opt-out. A customer's STOP is never overridden by staff."""
    from app.models.audit_log import AuditLog
    p = norm_phone(body.phone)
    if len(p) < 8:
        raise HTTPException(422, "Enter the phone in international format, e.g. +254712345678.")
    if body.status == "OPTED_IN":
        if not (body.proof or "").strip():
            raise HTTPException(422, "Describe how the customer agreed to WhatsApp messages (proof).")
        c = await _consent(db, p)
        if c is not None and c.status == "OPTED_OUT":
            raise HTTPException(409, f"{p} opted out; only the customer can opt back in (by replying START).")
    await _set_consent(db, p, body.status, f"manual:{current_user.username}", text=(body.proof or "").strip() or None,
                       user_id=current_user.id)
    db.add(AuditLog(actor_id=current_user.id, actor_email=getattr(current_user, "email", None),
                    actor_name=getattr(current_user, "full_name", None), event_type="WHATSAPP_CONSENT_RECORDED",
                    module="whatsapp", target_type="whatsapp_consent", target_id=p, details={"status": body.status}))
    await db.commit()
    return {"phone": p, "status": body.status}


# ── Config ────────────────────────────────────────────────────────────────────

@router.get("/configs", response_model=List[WAConfigRead])
async def list_configs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(WhatsAppConfig).where(WhatsAppConfig.is_active.is_(True)).order_by(WhatsAppConfig.created_at)
    )
    return [WAConfigRead.model_validate(c) for c in result.scalars().all()]


@router.post("/configs", response_model=WAConfigRead, status_code=201)
async def add_config(
    body: WAConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = WhatsAppConfig(**body.model_dump(), created_by_id=current_user.id)
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return WAConfigRead.model_validate(config)


@router.patch("/configs/{config_id}", response_model=WAConfigRead)
async def update_config(
    config_id: uuid.UUID,
    body: WAConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    config = await db.get(WhatsAppConfig, config_id)
    if not config or not config.is_active:
        raise HTTPException(404, "WhatsApp config not found or inactive")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    await db.commit()
    await db.refresh(config)
    return WAConfigRead.model_validate(config)


# ── Send Messages ─────────────────────────────────────────────────────────────

async def _get_config_or_404(db: AsyncSession, config_id: uuid.UUID) -> WhatsAppConfig:
    c = await db.get(WhatsAppConfig, config_id)
    if not c or not c.is_active:
        raise HTTPException(404, "WhatsApp config not found or inactive")
    return c


@router.post("/send/text", response_model=WAMessageRead, status_code=201)
async def send_text(
    body: WASendText,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await _get_config_or_404(db, body.config_id)
    await _require_may_send(db, body.phone)

    if config.is_demo_mode:
        status = WAMessageStatus.DELIVERED
        external_id: Optional[str] = f"demo_{uuid.uuid4().hex[:12]}"
        error_msg: Optional[str] = None
        delivered_at: Optional[datetime] = datetime.now(tz=timezone.utc)
    else:
        if not config.api_token or not config.business_phone_id:
            raise HTTPException(400, "Live mode requires api_token and business_phone_id in WhatsApp config")
        external_id, error_msg = await _meta_send_text(
            config.business_phone_id, config.api_token, body.phone, body.body
        )
        status = WAMessageStatus.SENT if external_id else WAMessageStatus.FAILED
        delivered_at = None

    msg = WhatsAppMessage(
        config_id=config.id,
        direction=WAMessageDirection.OUTBOUND,
        message_type=WAMessageType.TEXT,
        status=status,
        phone=body.phone,
        contact_name=body.contact_name,
        body=body.body,
        external_msg_id=external_id,
        error_message=error_msg,
        delivered_at=delivered_at,
        linked_module=body.linked_module,
        linked_object_id=body.linked_object_id,
        linked_object_ref=body.linked_object_ref,
        sent_by_id=current_user.id,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return WAMessageRead.model_validate(msg)


@router.post("/send/template", response_model=WAMessageRead, status_code=201)
async def send_template(
    body: WASendTemplate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = await _get_config_or_404(db, body.config_id)
    await _require_may_send(db, body.phone)

    # Resolve template for body rendering and language
    tmpl_q = await db.execute(
        select(WhatsAppTemplate).where(WhatsAppTemplate.template_name == body.template_name)
    )
    tmpl = tmpl_q.scalar_one_or_none()
    rendered_body = None
    if tmpl:
        rendered_body = tmpl.body_template
        for i, var in enumerate(body.variables, start=1):
            rendered_body = rendered_body.replace(f"{{{{{i}}}}}", var)

    if config.is_demo_mode:
        status = WAMessageStatus.DELIVERED
        external_id = f"demo_{uuid.uuid4().hex[:12]}"
        error_msg = None
        delivered_at = datetime.now(tz=timezone.utc)
    else:
        if not config.api_token or not config.business_phone_id:
            raise HTTPException(400, "Live mode requires api_token and business_phone_id in WhatsApp config")
        language = tmpl.language if tmpl else "en"
        external_id, error_msg = await _meta_send_template(
            config.business_phone_id, config.api_token, body.phone,
            body.template_name, language, body.variables,
        )
        status = WAMessageStatus.SENT if external_id else WAMessageStatus.FAILED
        delivered_at = None

    msg = WhatsAppMessage(
        config_id=config.id,
        direction=WAMessageDirection.OUTBOUND,
        message_type=WAMessageType.TEMPLATE,
        status=status,
        phone=body.phone,
        contact_name=body.contact_name,
        body=rendered_body,
        template_name=body.template_name,
        template_vars=body.variables,
        external_msg_id=external_id,
        error_message=error_msg,
        delivered_at=delivered_at,
        linked_module=body.linked_module,
        linked_object_id=body.linked_object_id,
        linked_object_ref=body.linked_object_ref,
        sent_by_id=current_user.id,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return WAMessageRead.model_validate(msg)


# ── Webhook ───────────────────────────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Meta webhook verification challenge."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    config_q = await db.execute(
        select(WhatsAppConfig).where(
            WhatsAppConfig.webhook_verify_token == token,
            WhatsAppConfig.is_active.is_(True),
        )
    )
    config = config_q.scalar_one_or_none()

    if mode == "subscribe" and config:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(403, "Webhook verification failed")


@router.post("/webhook", status_code=200, dependencies=[Depends(verify_meta_signature)])
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Process inbound WhatsApp messages from Meta webhook."""
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored"}

    # Parse Meta Cloud API format
    entries = payload.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            contacts = {c["wa_id"]: c.get("profile", {}).get("name") for c in value.get("contacts", [])}

            # Find matching config by phone number ID
            phone_id = value.get("metadata", {}).get("phone_number_id")
            config_q = await db.execute(
                select(WhatsAppConfig).where(
                    WhatsAppConfig.business_phone_id == phone_id,
                    WhatsAppConfig.is_active.is_(True),
                )
            )
            config = config_q.scalar_one_or_none()
            if not config:
                continue

            for wa_msg in messages:
                phone = wa_msg.get("from", "")
                body = wa_msg.get("text", {}).get("body") if wa_msg.get("type") == "text" else None
                msg = WhatsAppMessage(
                    config_id=config.id,
                    direction=WAMessageDirection.INBOUND,
                    message_type=WAMessageType.TEXT,
                    status=WAMessageStatus.DELIVERED,
                    phone=f"+{phone}",
                    contact_name=contacts.get(phone),
                    body=body,
                    external_msg_id=wa_msg.get("id"),
                )
                db.add(msg)
                await _handle_keywords(db, config, f"+{phone}", body)

            # Process status updates
            for status_update in value.get("statuses", []):
                msg_id = status_update.get("id")
                new_status = status_update.get("status", "").upper()
                if msg_id and new_status in WAMessageStatus.__members__:
                    existing_q = await db.execute(
                        select(WhatsAppMessage).where(WhatsAppMessage.external_msg_id == msg_id)
                    )
                    existing = existing_q.scalar_one_or_none()
                    if existing:
                        existing.status = WAMessageStatus[new_status]
                        if new_status == "DELIVERED":
                            existing.delivered_at = datetime.now(tz=timezone.utc)
                        elif new_status == "READ":
                            existing.read_at = datetime.now(tz=timezone.utc)

    await db.commit()
    return {"status": "ok"}


# ── Message Log ───────────────────────────────────────────────────────────────

@router.get("/messages", response_model=List[WAMessageRead])
async def list_messages(
    phone: Optional[str] = None,
    direction: Optional[WAMessageDirection] = None,
    linked_object_id: Optional[uuid.UUID] = None,
    config_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(WhatsAppMessage).order_by(WhatsAppMessage.created_at.desc()).offset(skip).limit(limit)
    if phone:
        q = q.where(WhatsAppMessage.phone == phone)
    if direction:
        q = q.where(WhatsAppMessage.direction == direction)
    if linked_object_id:
        q = q.where(WhatsAppMessage.linked_object_id == linked_object_id)
    if config_id:
        q = q.where(WhatsAppMessage.config_id == config_id)
    msgs = list((await db.execute(q)).scalars().all())
    return [WAMessageRead.model_validate(m) for m in msgs]


# ── Simulate Inbound (Demo) ───────────────────────────────────────────────────

@router.post("/simulate-inbound", response_model=WAMessageRead, status_code=201)
async def simulate_inbound(
    body: WASimulateInbound,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Demo: create a fake inbound message from a customer/supplier."""
    config = await _get_config_or_404(db, body.config_id)
    msg = WhatsAppMessage(
        config_id=config.id,
        direction=WAMessageDirection.INBOUND,
        message_type=WAMessageType.TEXT,
        status=WAMessageStatus.DELIVERED,
        phone=body.phone,
        contact_name=body.contact_name,
        body=body.body,
        external_msg_id=f"sim_{uuid.uuid4().hex[:12]}",
        delivered_at=datetime.now(tz=timezone.utc),
        linked_module=body.linked_module,
        linked_object_id=body.linked_object_id,
        linked_object_ref=body.linked_object_ref,
    )
    db.add(msg)
    await _handle_keywords(db, config, body.phone, body.body)
    await db.commit()
    await db.refresh(msg)
    return WAMessageRead.model_validate(msg)


# ── Templates ─────────────────────────────────────────────────────────────────

@router.get("/templates", response_model=List[WATemplateRead])
async def list_templates(
    module_context: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(WhatsAppTemplate).where(WhatsAppTemplate.is_active.is_(True)).order_by(WhatsAppTemplate.display_name)
    if module_context:
        q = q.where(
            (WhatsAppTemplate.module_context == module_context) |
            (WhatsAppTemplate.module_context.is_(None))
        )
    return [WATemplateRead.model_validate(t) for t in (await db.execute(q)).scalars().all()]


@router.post("/templates", response_model=WATemplateRead, status_code=201)
async def create_template(
    body: WATemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = (await db.execute(
        select(WhatsAppTemplate).where(WhatsAppTemplate.template_name == body.template_name)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"Template '{body.template_name}' already exists")

    tmpl = WhatsAppTemplate(**body.model_dump(), created_by_id=current_user.id)
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return WATemplateRead.model_validate(tmpl)


@router.post("/seed-demo-templates", response_model=List[WATemplateRead], status_code=201)
async def seed_demo_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed standard FMCG WhatsApp templates for demo use."""
    demo_templates = [
        {
            "template_name": "order_confirmation",
            "display_name": "Order Confirmation",
            "category": "UTILITY",
            "header_text": "Order Confirmed ✅",
            "body_template": "Dear {{1}}, your order *{{2}}* for {{3}} has been confirmed. "
                             "Estimated delivery: {{4}}. Track at {{5}}.",
            "variable_count": 5,
            "module_context": "sales",
        },
        {
            "template_name": "invoice_reminder",
            "display_name": "Invoice Payment Reminder",
            "category": "UTILITY",
            "header_text": "Payment Reminder",
            "body_template": "Dear {{1}}, invoice *{{2}}* for KES {{3}} is due on {{4}}. "
                             "Please arrange payment to avoid disruption of services.",
            "footer_text": "Reply STOP to unsubscribe from reminders.",
            "variable_count": 4,
            "module_context": "finance",
        },
        {
            "template_name": "delivery_dispatch",
            "display_name": "Delivery Dispatched",
            "category": "UTILITY",
            "header_text": "Your Order is on the Way 🚚",
            "body_template": "Hi {{1}}! Order {{2}} has been dispatched. "
                             "Driver: {{3}} | Vehicle: {{4}} | ETA: {{5}}.",
            "variable_count": 5,
            "module_context": "delivery",
        },
        {
            "template_name": "po_approval_request",
            "display_name": "PO Approval Request",
            "category": "UTILITY",
            "body_template": "Action Required: Purchase Order *{{1}}* for KES {{2}} requires your approval. "
                             "Supplier: {{3}}. Please log in to approve.",
            "variable_count": 3,
            "module_context": "procurement",
        },
        {
            "template_name": "quality_hold_alert",
            "display_name": "Quality Hold Alert",
            "category": "UTILITY",
            "header_text": "⚠ Quality Hold",
            "body_template": "Quality Alert: Batch *{{1}}* of product {{2}} has been placed on hold. "
                             "Reason: {{3}}. Do not dispatch until cleared by QC.",
            "variable_count": 3,
            "module_context": "quality",
        },
    ]

    created = []
    for td in demo_templates:
        existing = (await db.execute(
            select(WhatsAppTemplate).where(WhatsAppTemplate.template_name == td["template_name"])
        )).scalar_one_or_none()
        if not existing:
            tmpl = WhatsAppTemplate(**td, language="en", is_active=True, created_by_id=current_user.id)
            db.add(tmpl)
            created.append(tmpl)

    await db.commit()
    for t in created:
        await db.refresh(t)
    return [WATemplateRead.model_validate(t) for t in created]
