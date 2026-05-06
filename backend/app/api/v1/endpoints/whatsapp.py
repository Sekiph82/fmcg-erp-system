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

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.whatsapp import (
    WhatsAppConfig, WhatsAppMessage, WhatsAppTemplate,
    WAMessageDirection, WAMessageType, WAMessageStatus,
)
from app.schemas.whatsapp import (
    WAConfigCreate, WAConfigRead,
    WASendText, WASendTemplate,
    WAMessageRead,
    WATemplateCreate, WATemplateRead,
    WASimulateInbound,
)

router = APIRouter()


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

    # In demo mode: immediately mark DELIVERED
    status = WAMessageStatus.DELIVERED if config.is_demo_mode else WAMessageStatus.QUEUED
    external_id = f"demo_{uuid.uuid4().hex[:12]}" if config.is_demo_mode else None

    msg = WhatsAppMessage(
        config_id=config.id,
        direction=WAMessageDirection.OUTBOUND,
        message_type=WAMessageType.TEXT,
        status=status,
        phone=body.phone,
        contact_name=body.contact_name,
        body=body.body,
        external_msg_id=external_id,
        delivered_at=datetime.now(tz=timezone.utc) if config.is_demo_mode else None,
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

    # Resolve template body for logging
    tmpl_q = await db.execute(
        select(WhatsAppTemplate).where(WhatsAppTemplate.template_name == body.template_name)
    )
    tmpl = tmpl_q.scalar_one_or_none()
    rendered_body = None
    if tmpl:
        rendered_body = tmpl.body_template
        for i, var in enumerate(body.variables, start=1):
            rendered_body = rendered_body.replace(f"{{{{{i}}}}}", var)

    status = WAMessageStatus.DELIVERED if config.is_demo_mode else WAMessageStatus.QUEUED
    external_id = f"demo_{uuid.uuid4().hex[:12]}" if config.is_demo_mode else None

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
        delivered_at=datetime.now(tz=timezone.utc) if config.is_demo_mode else None,
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


@router.post("/webhook", status_code=200)
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
