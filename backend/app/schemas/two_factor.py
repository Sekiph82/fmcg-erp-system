from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.models.two_factor import TwoFAMethod, TwoFASessionStatus


# ── Setup / Enable ────────────────────────────────────────────────────────────

class TwoFASetupRequest(BaseModel):
    method: TwoFAMethod = TwoFAMethod.TOTP
    phone_number: Optional[str] = None
    email: Optional[str] = None


class TwoFASetupResponse(BaseModel):
    method: TwoFAMethod
    secret_key: Optional[str] = None       # TOTP only
    qr_code_uri: Optional[str] = None      # otpauth:// URI for QR scanning
    qr_code_image: Optional[str] = None    # base64 PNG
    session_token: Optional[str] = None    # SMS/email only — pass to /verify


class TwoFAVerifySetupRequest(BaseModel):
    code: str
    session_token: Optional[str] = None   # required for SMS/email, omit for TOTP


# ── Resend OTP ────────────────────────────────────────────────────────────────

class OTPResendRequest(BaseModel):
    session_token: str


class OTPResendResponse(BaseModel):
    session_token: str      # new token — replace old one in client
    cooldown_seconds: int


class TwoFAEnableResponse(BaseModel):
    is_enabled: bool
    recovery_codes: List[str]              # plaintext, shown once


# ── Login verify ──────────────────────────────────────────────────────────────

class TwoFALoginVerifyRequest(BaseModel):
    session_token: str
    code: str


# ── Disable ───────────────────────────────────────────────────────────────────

class TwoFADisableRequest(BaseModel):
    password: str                          # require password confirmation


# ── Recovery codes ────────────────────────────────────────────────────────────

class RecoveryCodesResponse(BaseModel):
    codes: List[str]


class UseRecoveryCodeRequest(BaseModel):
    session_token: str
    code: str


# ── Settings read ─────────────────────────────────────────────────────────────

class TwoFASettingsRead(BaseModel):
    is_enabled: bool
    method: Optional[TwoFAMethod] = None
    has_recovery_codes: bool = False

    model_config = {"from_attributes": True}


# ── Step-up auth ──────────────────────────────────────────────────────────────

class StepUpRequest(BaseModel):
    code: str
    action: str                            # e.g. "financial_approval"


class StepUpResponse(BaseModel):
    authorized: bool
    stepup_token: Optional[str] = None    # short-lived JWT for sensitive action


# ── Security report ───────────────────────────────────────────────────────────

class TwoFAStatusReport(BaseModel):
    total_users: int
    users_with_2fa_enabled: int
    users_without_2fa: int
    method_breakdown: dict
    failed_attempts_last_24h: int
