"""M47.S01.T010 platform and service depth. Prefix /api/v1/platform-depth.

- /field-permissions          role → field → HIDDEN | READ_ONLY rules (superuser or roles.manage)
- /smart-properties/recompute recompute rule-filled contact properties (crm.edit_all)
- /lead-forms/{id}/skip-if-known  form shortening settings (crm.edit_all)
- /slack/routes               event type → Slack webhook routing (crm.edit_all)
- /slack/link                 the signed-in user links their own Slack user id (verified by their account e-mail)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_any_permission
from app.core.deps import get_current_user, get_db
from app.models.m47_platform import FieldPermissionRule, SlackRoute, SlackUserLink
from app.services import pat_service as pats
from app.services import sensitive_service as sens

router = APIRouter()


def _need(u, perms: tuple[str, ...], msg: str) -> None:
    if not (u.is_superuser or has_any_permission(u, perms)):
        raise HTTPException(403, msg)


# ── field-level permissions ──────────────────────────────────────────────────

class RuleIn(BaseModel):
    entity: str = Field(min_length=1, max_length=60)
    role_name: str = Field(min_length=1, max_length=100)
    field_key: str = Field(min_length=1, max_length=60)
    access: Literal["HIDDEN", "READ_ONLY"]


def _rule_out(r: FieldPermissionRule) -> dict:
    return {"id": str(r.id), "entity": r.entity, "role_name": r.role_name, "field_key": r.field_key, "access": r.access}


@router.get("/field-permissions")
async def list_rules(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need(current_user, ("roles.manage",), "Only administrators manage field permissions.")
    from app.models.custom_objects import CustomObjectType
    from app.models.role import Role
    rules = (await db.execute(select(FieldPermissionRule).order_by(FieldPermissionRule.entity, FieldPermissionRule.role_name,
                                                                  FieldPermissionRule.field_key))).scalars()
    types = (await db.execute(select(CustomObjectType).order_by(CustomObjectType.key))).scalars()
    return {"rules": [_rule_out(r) for r in rules],
            "roles": list((await db.execute(select(Role.name).order_by(Role.name))).scalars()),
            "entities": [{"entity": "contact", "fields": list(sens.CONTACT_FIELDS)}]
            + [{"entity": f"co:{t.key}", "fields": [f["key"] for f in t.fields]} for t in types]}


@router.put("/field-permissions")
async def set_rule(body: RuleIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from sqlalchemy.dialects.postgresql import insert
    from app.models.role import Role
    _need(current_user, ("roles.manage",), "Only administrators manage field permissions.")
    try:
        await sens.validate_rule(db, body.entity, body.field_key, body.access)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if (await db.execute(select(Role.id).where(Role.name == body.role_name))).first() is None:
        raise HTTPException(422, "Unknown role.")
    await db.execute(insert(FieldPermissionRule).values(id=uuid.uuid4(), entity=body.entity, role_name=body.role_name,
                                                        field_key=body.field_key, access=body.access, created_by=current_user.username)
                     .on_conflict_do_update(constraint="uq_field_permission_rule", set_={"access": body.access}))
    pats.audit(db, current_user, "FIELD_PERMISSION_SET", "field_permission", f"{body.entity}:{body.role_name}:{body.field_key}",
               body.model_dump())
    await db.commit()
    return {"ok": True}


@router.delete("/field-permissions/{rule_id}", status_code=204)
async def delete_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need(current_user, ("roles.manage",), "Only administrators manage field permissions.")
    r = await db.get(FieldPermissionRule, rule_id)
    if r is None:
        raise HTTPException(404, "Rule not found")
    pats.audit(db, current_user, "FIELD_PERMISSION_REMOVED", "field_permission", f"{r.entity}:{r.role_name}:{r.field_key}", {})
    await db.delete(r)
    await db.commit()


# ── smart properties ────────────────────────────────────────────────────────

@router.post("/smart-properties/recompute")
async def recompute_smart(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services import crm_contact_service as cs
    _need(current_user, ("crm.edit_all",), "CRM administrators only.")
    n = await cs.recompute_smart_properties(db)
    await db.commit()
    return {"changed": n}


# ── lead form shortening ─────────────────────────────────────────────────────

class SkipIn(BaseModel):
    fields: list[str] = Field(max_length=4)


@router.get("/lead-forms/{form_id}/skip-if-known")
async def get_skip(form_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.models.crm import CRMLeadForm
    from app.services import crm_lead_capture_service as capture
    _need(current_user, ("crm.view", "crm.view_all", "crm.edit_all"), "CRM users only.")
    form = await db.get(CRMLeadForm, form_id)
    if form is None:
        raise HTTPException(404, "Form not found")
    return {"fields": await capture.skip_list(db, form), "skippable": list(capture.SKIPPABLE)}


@router.put("/lead-forms/{form_id}/skip-if-known")
async def put_skip(form_id: uuid.UUID, body: SkipIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.models.crm import CRMLeadForm
    from app.services import crm_lead_capture_service as capture
    _need(current_user, ("crm.edit_all",), "CRM administrators only.")
    form = await db.get(CRMLeadForm, form_id)
    if form is None:
        raise HTTPException(404, "Form not found")
    try:
        fields = await capture.set_skip_list(db, form, body.fields)
    except ValueError as e:
        raise HTTPException(422, str(e))
    pats.audit(db, current_user, "LEAD_FORM_SKIP_SET", "crm_lead_form", str(form.id), {"fields": fields})
    await db.commit()
    return {"fields": fields}


# ── Slack routing and user links ─────────────────────────────────────────────

class RouteIn(BaseModel):
    event_type: Literal["DEAL", "TICKET", "APPROVAL", "APPROVE"]
    channel_label: str = Field(min_length=1, max_length=80)
    webhook_url: str = Field(min_length=10, max_length=500)
    active: bool = True


@router.get("/slack/routes")
async def list_routes(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from app.services import messaging_service as ms
    _need(current_user, ("crm.edit_all",), "CRM administrators only.")
    rows = (await db.execute(select(SlackRoute).order_by(SlackRoute.event_type))).scalars()
    return {"signing_secret_configured": bool(ms.slack_signing_secret()),
            "routes": [{"id": str(r.id), "event_type": r.event_type, "channel_label": r.channel_label, "active": r.active,
                        "webhook": r.webhook_url.split("/services/")[0] + "/services/…"} for r in rows]}   # URL is a secret


@router.put("/slack/routes")
async def put_route(body: RouteIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    from sqlalchemy.dialects.postgresql import insert
    from app.services import messaging_service as ms
    _need(current_user, ("crm.edit_all",), "CRM administrators only.")
    if not ms.valid_webhook(body.webhook_url):
        raise HTTPException(422, "Use a Slack incoming-webhook URL (https://hooks.slack.com/services/...).")
    await db.execute(insert(SlackRoute).values(id=uuid.uuid4(), event_type=body.event_type, channel_label=body.channel_label,
                                               webhook_url=body.webhook_url, active=body.active, created_by=current_user.username)
                     .on_conflict_do_update(index_elements=["event_type"], set_={
                         "channel_label": body.channel_label, "webhook_url": body.webhook_url, "active": body.active}))
    pats.audit(db, current_user, "SLACK_ROUTE_SET", "slack_route", body.event_type, {"channel": body.channel_label, "active": body.active})
    await db.commit()
    return {"ok": True}


@router.delete("/slack/routes/{event_type}", status_code=204)
async def delete_route(event_type: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    _need(current_user, ("crm.edit_all",), "CRM administrators only.")
    r = (await db.execute(select(SlackRoute).where(SlackRoute.event_type == event_type))).scalar_one_or_none()
    if r is None:
        raise HTTPException(404, "Route not found")
    await db.delete(r)
    pats.audit(db, current_user, "SLACK_ROUTE_REMOVED", "slack_route", event_type, {})
    await db.commit()


class LinkIn(BaseModel):
    slack_user_id: str = Field(pattern=r"^[UW][A-Z0-9]{2,39}$")


@router.get("/slack/link")
async def my_link(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    r = (await db.execute(select(SlackUserLink).where(SlackUserLink.user_id == current_user.id))).scalar_one_or_none()
    return {"slack_user_id": r.slack_user_id if r else None, "email": r.email if r else None}


@router.put("/slack/link")
async def link_me(body: LinkIn, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Link your own Slack user id. The link records your account e-mail; if the e-mail changes the link stops working."""
    if not current_user.email:
        raise HTTPException(422, "Your account has no e-mail address.")
    taken = await db.get(SlackUserLink, body.slack_user_id)
    if taken is not None and taken.user_id != current_user.id:
        raise HTTPException(409, "This Slack user is linked to another ERP user.")
    old = (await db.execute(select(SlackUserLink).where(SlackUserLink.user_id == current_user.id))).scalar_one_or_none()
    if old is not None:
        await db.delete(old)
        await db.flush()
    db.add(SlackUserLink(slack_user_id=body.slack_user_id, user_id=current_user.id, email=current_user.email.lower(),
                         verified_at=datetime.now(timezone.utc)))
    pats.audit(db, current_user, "SLACK_USER_LINKED", "user", str(current_user.id), {"slack_user_id": body.slack_user_id})
    await db.commit()
    return {"slack_user_id": body.slack_user_id}


@router.delete("/slack/link", status_code=204)
async def unlink_me(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    r = (await db.execute(select(SlackUserLink).where(SlackUserLink.user_id == current_user.id))).scalar_one_or_none()
    if r is not None:
        await db.delete(r)
        await db.commit()


@router.get("/status")
async def status(current_user=Depends(get_current_user)):
    """What is configured (no secrets)."""
    from app.services import ads_adapters as ads
    from app.services import messaging_service as ms
    return {"slack_signing_secret": bool(ms.slack_signing_secret()), "meta_pixel": bool(ads._setting("META_PIXEL_ID")),
            "google_conversion_action": bool(ads._setting("GOOGLE_ADS_CONVERSION_ACTION")),
            "meta_ads": ads.ADAPTERS["meta"].configured(), "google_ads": ads.ADAPTERS["google"].configured()}

