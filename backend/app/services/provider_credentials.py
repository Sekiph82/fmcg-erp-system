"""Provider credentials entered from the app (owner 2026-11-20): M-Pesa, SMS, WhatsApp and outgoing e-mail.

The owner types the keys once in Integrations → Provider keys; they are stored encrypted (Fernet, key derived from
SECRET_KEY) in system_configs and applied onto the running settings, so every service that reads settings.MPESA_*,
settings.SMS_*, settings.WHATSAPP_* or settings.SMTP_* uses them at once. Other workers pick them up within a minute
(refresh loop in main.py). Values from .env stay the fallback; a blank secret in the form keeps the stored one.
Secrets never leave the server: the API reports only whether each one is set.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import select

from app.core.config import settings

log = logging.getLogger(__name__)
KEY_PREFIX = "provider_credentials."

# provider -> [(form field, settings attribute, label, secret?)]
PROVIDERS: dict[str, dict[str, Any]] = {
    "mpesa": {"label": "M-Pesa (Safaricom Daraja)", "fields": [
        ("environment", "MPESA_ENV", "Environment (sandbox or production)", False),
        ("shortcode", "MPESA_SHORTCODE", "Paybill / till number (shortcode)", False),
        ("transaction_type", "MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline or CustomerBuyGoodsOnline", False),
        ("consumer_key", "MPESA_CONSUMER_KEY", "Consumer key", True),
        ("consumer_secret", "MPESA_CONSUMER_SECRET", "Consumer secret", True),
        ("passkey", "MPESA_PASSKEY", "Lipa na M-Pesa passkey", True),
        ("callback_url", "MPESA_CALLBACK_URL", "Callback URL (public address of this server)", False),
        ("callback_secret", "MPESA_CALLBACK_SECRET", "Callback secret token", True),
    ]},
    "sms": {"label": "SMS", "fields": [
        ("provider", "SMS_PROVIDER", "Provider: africastalking or twilio", False),
        ("account", "SMS_ACCOUNT_SID", "Username (Africa's Talking) or Account SID (Twilio)", False),
        ("api_key", "SMS_AUTH_TOKEN", "API key / auth token", True),
        ("sender_id", "SMS_SENDER_ID", "Sender ID or from-number", False),
    ]},
    "whatsapp": {"label": "WhatsApp Business (Meta Cloud API)", "fields": [
        ("phone_number_id", "WHATSAPP_PHONE_NUMBER_ID", "Phone number ID", False),
        ("access_token", "WHATSAPP_ACCESS_TOKEN", "Permanent access token", True),
        ("app_secret", "WHATSAPP_APP_SECRET", "App secret (verifies incoming webhooks)", True),
    ]},
    "email": {"label": "Outgoing e-mail (SMTP) — invoices, campaigns", "fields": [
        ("host", "SMTP_HOST", "SMTP server", False),
        ("port", "SMTP_PORT", "Port (587)", False),
        ("username", "SMTP_USERNAME", "Username", False),
        ("password", "SMTP_PASSWORD", "Password", True),
        ("from_email", "SMTP_FROM_EMAIL", "From address", False),
        ("enabled", "CRM_OUTBOUND_EMAIL_ENABLED", "Send e-mail (true/false)", False),
    ]},
}
REQUIRED = {"mpesa": ("shortcode", "consumer_key", "consumer_secret", "passkey"), "sms": ("provider", "account", "api_key"),
            "whatsapp": ("phone_number_id", "access_token"), "email": ("host", "from_email")}


def _cipher() -> Fernet:
    key = hashlib.sha256(b"fmcg-erp:provider-credentials:v1\0" + settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


async def _load(db) -> dict[str, dict[str, str]]:
    from app.models.utilities import SystemConfig

    out = {}
    for cfg in (await db.execute(select(SystemConfig).where(SystemConfig.key.like(f"{KEY_PREFIX}%")))).scalars():
        name = cfg.key[len(KEY_PREFIX):]
        try:
            out[name] = json.loads(_cipher().decrypt(cfg.value.encode()).decode()) if cfg.value else {}
        except (InvalidToken, ValueError):
            log.error("provider credentials %s cannot be decrypted (SECRET_KEY changed?)", name)
    return out


def _coerce(attr: str, value: str):
    current = getattr(settings, attr, None)
    if isinstance(current, bool):
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    if isinstance(current, int):
        return int(value)
    return value


async def apply(db) -> None:
    """Put stored credentials onto the live settings (startup, refresh loop, after a save)."""
    stored = await _load(db)
    for name, values in stored.items():
        for field, attr, _, _ in PROVIDERS.get(name, {}).get("fields", []):
            if values.get(field) not in (None, ""):
                try:
                    setattr(settings, attr, _coerce(attr, values[field]))
                except ValueError:
                    log.warning("provider %s: bad value for %s", name, field)


async def status(db) -> list[dict]:
    stored = await _load(db)
    out = []
    for name, spec in PROVIDERS.items():
        values = stored.get(name, {})
        fields = []
        for field, attr, label, secret in spec["fields"]:
            current = values.get(field) or getattr(settings, attr, "") or ""
            fields.append({"field": field, "label": label, "secret": secret, "is_set": bool(str(current).strip()),
                           "value": None if secret else str(current)})
        configured = all(next(f for f in fields if f["field"] == r)["is_set"] for r in REQUIRED[name])
        out.append({"provider": name, "label": spec["label"], "configured": configured, "fields": fields})
    return out


async def save(db, provider: str, values: dict, user_id) -> None:
    from app.models.utilities import ConfigCategory, SystemConfig

    spec = PROVIDERS.get(provider)
    if spec is None:
        raise HTTPException(404, "Unknown provider")
    allowed = {f[0]: f for f in spec["fields"]}
    unknown = set(values) - set(allowed)
    if unknown:
        raise HTTPException(422, f"Unknown fields: {', '.join(sorted(unknown))}")
    merged = dict((await _load(db)).get(provider, {}))
    for field, raw in values.items():
        value = "" if raw is None else str(raw).strip()
        if "\n" in value or "\r" in value or len(value) > 2000:
            raise HTTPException(422, f"{field}: invalid value")
        if allowed[field][3] and value == "":
            continue  # blank secret = keep the stored one
        try:
            _coerce(allowed[field][1], value) if value else None
        except ValueError:
            raise HTTPException(422, f"{field}: must be a number") from None
        merged[field] = value
    if provider == "mpesa" and merged.get("environment") not in (None, "", "sandbox", "production"):
        raise HTTPException(422, "environment must be sandbox or production")
    if provider == "sms" and merged.get("provider") not in (None, "", "twilio", "africastalking"):
        raise HTTPException(422, "SMS provider must be africastalking or twilio")
    key = KEY_PREFIX + provider
    cfg = (await db.execute(select(SystemConfig).where(SystemConfig.key == key))).scalar_one_or_none()
    if cfg is None:
        cfg = SystemConfig(key=key, category=ConfigCategory.SYSTEM, is_editable=False,
                           description=f"{spec['label']} credentials (encrypted)")
        db.add(cfg)
    cfg.value = _cipher().encrypt(json.dumps(merged).encode()).decode()
    cfg.updated_by_id = user_id
    await db.flush()
    await apply(db)
