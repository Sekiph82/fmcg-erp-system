"""TOTP / OTP utilities for 2FA."""
from __future__ import annotations
import base64
import io
import os
import secrets
import string
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode
from passlib.context import CryptContext

from app.core.config import settings

_code_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Recovery codes: 10 random codes, 8 chars each (base32-ish)
RECOVERY_CODE_COUNT = 10
TOTP_WINDOW = 1          # ±30-second window tolerance
EMAIL_SMS_TTL_SECONDS = 300   # 5 minutes
STEPUP_TTL_SECONDS = 300


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=username,
        issuer_name=settings.PROJECT_NAME,
    )


def generate_qr_base64(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=TOTP_WINDOW)


def generate_otp() -> str:
    """6-digit numeric OTP for SMS/email."""
    return "".join(secrets.choice(string.digits) for _ in range(6))


def otp_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=EMAIL_SMS_TTL_SECONDS)


def stepup_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=STEPUP_TTL_SECONDS)


# ── Recovery codes ────────────────────────────────────────────────────────────

def generate_recovery_codes() -> list[str]:
    alphabet = string.ascii_uppercase + string.digits
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = "".join(secrets.choice(alphabet) for _ in range(8))
        formatted = f"{raw[:4]}-{raw[4:]}"  # XXXX-XXXX
        codes.append(formatted)
    return codes


def hash_recovery_code(code: str) -> str:
    return _code_context.hash(code.replace("-", "").upper())


def verify_recovery_code(plain: str, hashed: str) -> bool:
    return _code_context.verify(plain.replace("-", "").upper(), hashed)


# ── Step-up token ─────────────────────────────────────────────────────────────

def create_stepup_token(user_id: str, action: str) -> str:
    from datetime import timedelta
    from app.core.security import create_access_token
    import json
    subject = json.dumps({"uid": user_id, "action": action, "type": "stepup"})
    return create_access_token(subject, expires_delta=timedelta(seconds=STEPUP_TTL_SECONDS))


def decode_stepup_token(token: str) -> dict | None:
    from app.core.security import decode_token
    import json
    raw = decode_token(token)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if data.get("type") != "stepup":
            return None
        return data
    except Exception:
        return None


# ── Pending-2FA session token ─────────────────────────────────────────────────

def create_pending_2fa_token(user_id: str, session_id: str) -> str:
    from datetime import timedelta
    from app.core.security import create_access_token
    import json
    subject = json.dumps({"uid": user_id, "sid": session_id, "type": "2fa_pending"})
    return create_access_token(subject, expires_delta=timedelta(seconds=EMAIL_SMS_TTL_SECONDS))


def decode_pending_2fa_token(token: str) -> dict | None:
    from app.core.security import decode_token
    import json
    raw = decode_token(token)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if data.get("type") != "2fa_pending":
            return None
        return data
    except Exception:
        return None
