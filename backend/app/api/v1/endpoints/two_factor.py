"""Two-Factor Authentication endpoints."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.auth_cookies import set_auth_cookie
from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.core import totp as totp_utils
from app.crud import two_factor as tfa_crud
from app.crud import audit as audit_crud
from app.models.two_factor import TwoFAMethod, TwoFASessionStatus, User2FASettings
from app.models.audit_log import AuditEvent
from app.models.user import User
from app.schemas.two_factor import (
    TwoFASetupRequest, TwoFASetupResponse,
    TwoFAVerifySetupRequest, TwoFAEnableResponse,
    TwoFALoginVerifyRequest,
    TwoFADisableRequest,
    RecoveryCodesResponse, UseRecoveryCodeRequest,
    TwoFASettingsRead,
    StepUpRequest, StepUpResponse,
    TwoFAStatusReport,
    OTPResendRequest, OTPResendResponse,
)

router = APIRouter()

MAX_ATTEMPTS = 5


def _ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )


# ── GET /auth/2fa/settings ────────────────────────────────────────────────────

@router.get("/settings", response_model=TwoFASettingsRead)
async def get_2fa_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await tfa_crud.get_2fa_settings(db, current_user.id)
    if not settings:
        return TwoFASettingsRead(is_enabled=False)
    from app.crud.two_factor import get_unused_recovery_codes
    codes = await get_unused_recovery_codes(db, current_user.id)
    return TwoFASettingsRead(
        is_enabled=settings.is_enabled,
        method=settings.method,
        has_recovery_codes=len(codes) > 0,
    )


# ── POST /auth/2fa/setup ──────────────────────────────────────────────────────

@router.post("/setup", response_model=TwoFASetupResponse)
async def setup_2fa(
    body: TwoFASetupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate 2FA setup. For TOTP, returns secret + QR. For email/SMS, sends OTP."""
    settings = await tfa_crud.get_or_create_2fa_settings(db, current_user.id, body.method)

    if body.method == TwoFAMethod.TOTP:
        secret = totp_utils.generate_totp_secret()
        settings.secret_key = secret
        settings.method = TwoFAMethod.TOTP
        await db.commit()

        uri = totp_utils.get_totp_uri(secret, current_user.username)
        qr = totp_utils.generate_qr_base64(uri)
        return TwoFASetupResponse(
            method=TwoFAMethod.TOTP,
            secret_key=secret,
            qr_code_uri=uri,
            qr_code_image=qr,
        )

    if body.method == TwoFAMethod.SMS:
        if not body.phone_number:
            raise HTTPException(status_code=422, detail="phone_number required for SMS method")
        settings.method = TwoFAMethod.SMS
        settings.phone_number = body.phone_number
        otp = totp_utils.generate_otp()
        session = await tfa_crud.create_2fa_session(
            db, user_id=current_user.id, settings_id=settings.id,
            method=TwoFAMethod.SMS, challenge_code=totp_utils.hash_otp(otp),
        )
        await db.commit()
        from app.services.sms_sender import send_otp_sms
        await send_otp_sms(body.phone_number, otp)
        setup_token = totp_utils.create_setup_2fa_token(str(current_user.id), str(session.id))
        return TwoFASetupResponse(method=TwoFAMethod.SMS, session_token=setup_token)

    if body.method == TwoFAMethod.EMAIL:
        settings.method = TwoFAMethod.EMAIL
        settings.email = body.email or current_user.email
        otp = totp_utils.generate_otp()
        session = await tfa_crud.create_2fa_session(
            db, user_id=current_user.id, settings_id=settings.id,
            method=TwoFAMethod.EMAIL, challenge_code=totp_utils.hash_otp(otp),
        )
        await db.commit()
        from app.services.email_sender import send_otp_email
        dest = body.email or current_user.email
        await send_otp_email(dest, otp)
        setup_token = totp_utils.create_setup_2fa_token(str(current_user.id), str(session.id))
        return TwoFASetupResponse(method=TwoFAMethod.EMAIL, session_token=setup_token)

    raise HTTPException(status_code=422, detail="Unsupported 2FA method")


# ── POST /auth/2fa/verify ─────────────────────────────────────────────────────

@router.post("/verify", response_model=TwoFAEnableResponse)
async def verify_and_enable_2fa(
    body: TwoFAVerifySetupRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify first OTP during setup, then enable 2FA and return recovery codes."""
    tfa_settings = await tfa_crud.get_2fa_settings(db, current_user.id)
    if not tfa_settings:
        raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /setup first.")

    if tfa_settings.method == TwoFAMethod.TOTP:
        if not tfa_settings.secret_key:
            raise HTTPException(status_code=400, detail="2FA setup not initiated. Call /setup first.")
        if not totp_utils.verify_totp(tfa_settings.secret_key, body.code):
            raise HTTPException(status_code=400, detail="Invalid OTP code")
    else:
        # SMS/email: verify via setup session token
        if not body.session_token:
            raise HTTPException(
                status_code=422,
                detail="session_token required for SMS/email 2FA verification",
            )
        payload = totp_utils.decode_setup_2fa_token(body.session_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired setup token")
        session_id = uuid.UUID(payload["sid"])
        session = await tfa_crud.get_2fa_session(db, session_id)
        if not session or session.status != TwoFASessionStatus.PENDING:
            raise HTTPException(status_code=401, detail="Setup session not found or already used")
        if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            session.status = TwoFASessionStatus.EXPIRED
            await db.commit()
            raise HTTPException(status_code=401, detail="Setup OTP expired. Request a new one via /setup.")
        if int(session.attempt_count) >= MAX_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Request a new code.")
        if not session.challenge_code or not totp_utils.verify_otp_hash(body.code, session.challenge_code):
            session = await tfa_crud.mark_session_failed(db, session)
            await db.commit()
            remaining = MAX_ATTEMPTS - int(session.attempt_count)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid OTP code. {remaining} attempt(s) remaining.",
            )
        await tfa_crud.mark_session_verified(db, session)
    settings = tfa_settings

    # Enable
    settings.is_enabled = True

    # Generate recovery codes
    await tfa_crud.delete_recovery_codes(db, current_user.id)
    plain_codes = totp_utils.generate_recovery_codes()
    await tfa_crud.create_recovery_codes(db, current_user.id, settings.id, plain_codes)

    await audit_crud.log_event(
        db,
        event_type=AuditEvent.TWO_FA_ENABLED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(current_user.id),
        target_name=current_user.email,
        details={"method": settings.method},
        ip_address=_ip(request),
    )
    await db.commit()
    return TwoFAEnableResponse(is_enabled=True, recovery_codes=plain_codes)


# ── POST /auth/2fa/enable ─────────────────────────────────────────────────────

@router.post("/enable", response_model=TwoFAEnableResponse)
async def enable_2fa(
    body: TwoFAVerifySetupRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias for /verify — enables 2FA after confirming OTP."""
    return await verify_and_enable_2fa(body, request, current_user, db)


# ── POST /auth/2fa/disable ────────────────────────────────────────────────────

@router.post("/disable")
async def disable_2fa(
    body: TwoFADisableRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="Password incorrect")

    settings = await tfa_crud.get_2fa_settings(db, current_user.id)
    if not settings:
        raise HTTPException(status_code=400, detail="2FA not configured")

    settings.is_enabled = False
    settings.secret_key = None
    await tfa_crud.delete_recovery_codes(db, current_user.id)

    await audit_crud.log_event(
        db,
        event_type=AuditEvent.TWO_FA_DISABLED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(current_user.id),
        target_name=current_user.email,
        ip_address=_ip(request),
    )
    await db.commit()
    return {"detail": "2FA disabled"}


# ── POST /auth/2fa/login-verify ───────────────────────────────────────────────

@router.post("/login-verify")
async def login_verify_2fa(
    body: TwoFALoginVerifyRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Verify 2FA code during login flow. Returns full access_token on success."""
    payload = totp_utils.decode_pending_2fa_token(body.session_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired 2FA session token")

    session_id = uuid.UUID(payload["sid"])
    user_id = uuid.UUID(payload["uid"])

    session = await tfa_crud.get_2fa_session(db, session_id)
    if not session:
        raise HTTPException(status_code=401, detail="2FA session not found")

    if session.status != TwoFASessionStatus.PENDING:
        raise HTTPException(status_code=401, detail="2FA session already used or expired")

    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        session.status = TwoFASessionStatus.EXPIRED
        await db.commit()
        raise HTTPException(status_code=401, detail="2FA session expired")

    if int(session.attempt_count) >= MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many failed attempts. Request a new login.")

    # Get 2FA settings
    tfa_settings = await tfa_crud.get_2fa_settings(db, user_id)
    if not tfa_settings:
        raise HTTPException(status_code=500, detail="2FA settings not found")

    # Verify code
    verified = False
    if session.method == TwoFAMethod.TOTP:
        if tfa_settings.secret_key:
            verified = totp_utils.verify_totp(tfa_settings.secret_key, body.code)
    else:
        # SMS or email: verify against bcrypt hash
        if session.challenge_code:
            verified = totp_utils.verify_otp_hash(body.code, session.challenge_code)

    if not verified:
        session = await tfa_crud.mark_session_failed(db, session)
        remaining = MAX_ATTEMPTS - int(session.attempt_count)

        await audit_crud.log_event(
            db,
            event_type=AuditEvent.TWO_FA_FAILED,
            actor_id=user_id,
            target_type="user",
            target_id=str(user_id),
            details={"method": session.method, "remaining_attempts": remaining},
            ip_address=_ip(request),
        )
        await db.commit()
        raise HTTPException(
            status_code=401,
            detail=f"Invalid 2FA code. {remaining} attempt(s) remaining.",
        )

    await tfa_crud.mark_session_verified(db, session)

    await audit_crud.log_event(
        db,
        event_type=AuditEvent.TWO_FA_SUCCESS,
        actor_id=user_id,
        target_type="user",
        target_id=str(user_id),
        details={"method": session.method},
        ip_address=_ip(request),
    )
    await db.commit()

    access_token = create_access_token(str(user_id))
    set_auth_cookie(response, access_token)
    return {
        "access_token": access_token if settings.AUTH_RETURN_TOKEN_IN_BODY else None,
        "token_type": "bearer",
    }


# ── GET /auth/2fa/recovery-codes ─────────────────────────────────────────────

@router.get("/recovery-codes", response_model=RecoveryCodesResponse)
async def list_recovery_codes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns count only (not plaintext) — plaintext only shown at setup."""
    codes = await tfa_crud.get_unused_recovery_codes(db, current_user.id)
    return RecoveryCodesResponse(codes=[f"Code {i+1} (hidden)" for i, _ in enumerate(codes)])


@router.post("/recovery-codes/regenerate", response_model=RecoveryCodesResponse)
async def regenerate_recovery_codes(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await tfa_crud.get_2fa_settings(db, current_user.id)
    if not settings or not settings.is_enabled:
        raise HTTPException(status_code=400, detail="2FA not enabled")

    await tfa_crud.delete_recovery_codes(db, current_user.id)
    plain_codes = totp_utils.generate_recovery_codes()
    await tfa_crud.create_recovery_codes(db, current_user.id, settings.id, plain_codes)

    await audit_crud.log_event(
        db,
        event_type=AuditEvent.TWO_FA_RECOVERY_REGENERATED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(current_user.id),
        ip_address=_ip(request),
    )
    await db.commit()
    return RecoveryCodesResponse(codes=plain_codes)


# ── POST /auth/2fa/use-recovery-code ─────────────────────────────────────────

@router.post("/use-recovery-code")
async def use_recovery_code(
    body: UseRecoveryCodeRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Use a backup recovery code instead of OTP during login."""
    payload = totp_utils.decode_pending_2fa_token(body.session_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired 2FA session token")

    user_id = uuid.UUID(payload["uid"])
    session_id = uuid.UUID(payload["sid"])

    session = await tfa_crud.get_2fa_session(db, session_id)
    if not session or session.status != TwoFASessionStatus.PENDING:
        raise HTTPException(status_code=401, detail="Invalid 2FA session")

    success = await tfa_crud.use_recovery_code(db, user_id, body.code)
    if not success:
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.TWO_FA_RECOVERY_FAILED,
            actor_id=user_id,
            target_type="user",
            target_id=str(user_id),
            ip_address=_ip(request),
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid or already used recovery code")

    session.status = TwoFASessionStatus.VERIFIED
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.TWO_FA_RECOVERY_USED,
        actor_id=user_id,
        target_type="user",
        target_id=str(user_id),
        ip_address=_ip(request),
    )
    await db.commit()

    access_token = create_access_token(str(user_id))
    set_auth_cookie(response, access_token)
    return {
        "access_token": access_token if settings.AUTH_RETURN_TOKEN_IN_BODY else None,
        "token_type": "bearer",
    }


# ── POST /auth/2fa/resend-otp ────────────────────────────────────────────────

@router.post("/resend-otp", response_model=OTPResendResponse)
async def resend_otp(
    body: OTPResendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Resend OTP for login or setup flow. Enforces 60-second cooldown."""
    from datetime import timedelta

    # Accept both login and setup tokens
    payload = totp_utils.decode_pending_2fa_token(body.session_token)
    token_type = "login"
    if not payload:
        payload = totp_utils.decode_setup_2fa_token(body.session_token)
        token_type = "setup"
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    session_id = uuid.UUID(payload["sid"])
    user_id = uuid.UUID(payload["uid"])

    session = await tfa_crud.get_2fa_session(db, session_id)
    if not session or session.status != TwoFASessionStatus.PENDING:
        raise HTTPException(status_code=401, detail="Session not found or already used")

    # Enforce resend cooldown
    cooldown = settings.OTP_RESEND_COOLDOWN_SECONDS
    elapsed = (datetime.now(timezone.utc) - session.created_at.replace(tzinfo=timezone.utc)).total_seconds()
    if elapsed < cooldown:
        remaining = int(cooldown - elapsed)
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {remaining}s before requesting a new code.",
        )

    tfa_settings = await tfa_crud.get_2fa_settings(db, user_id)
    if not tfa_settings:
        raise HTTPException(status_code=500, detail="2FA settings not found")

    # Expire old session, create new one
    session.status = TwoFASessionStatus.EXPIRED
    otp = totp_utils.generate_otp()
    new_session = await tfa_crud.create_2fa_session(
        db,
        user_id=user_id,
        settings_id=tfa_settings.id,
        method=session.method,
        challenge_code=totp_utils.hash_otp(otp),
    )
    await db.commit()

    # Dispatch
    from app.services.email_sender import send_otp_email
    from app.services.sms_sender import send_otp_sms
    try:
        if session.method == TwoFAMethod.EMAIL:
            dest = tfa_settings.email or ""
            await send_otp_email(dest, otp)
        else:
            await send_otp_sms(tfa_settings.phone_number or "", otp)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("OTP resend dispatch failed user=%s: %s", user_id, exc)

    if token_type == "login":
        new_token = totp_utils.create_pending_2fa_token(str(user_id), str(new_session.id))
    else:
        new_token = totp_utils.create_setup_2fa_token(str(user_id), str(new_session.id))

    return OTPResendResponse(session_token=new_token, cooldown_seconds=cooldown)


# ── POST /auth/2fa/step-up ────────────────────────────────────────────────────

@router.post("/step-up", response_model=StepUpResponse)
async def step_up_auth(
    body: StepUpRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify 2FA for a sensitive action. Returns short-lived step-up token."""
    settings = await tfa_crud.get_2fa_settings(db, current_user.id)
    if not settings or not settings.is_enabled:
        raise HTTPException(status_code=400, detail="2FA not enabled for this account")

    verified = False
    if settings.method == TwoFAMethod.TOTP and settings.secret_key:
        verified = totp_utils.verify_totp(settings.secret_key, body.code)

    if not verified:
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.TWO_FA_STEPUP_FAILED,
            actor_id=current_user.id,
            actor_email=current_user.email,
            target_type="action",
            target_name=body.action,
            ip_address=_ip(request),
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    stepup_token = totp_utils.create_stepup_token(str(current_user.id), body.action)

    await audit_crud.log_event(
        db,
        event_type=AuditEvent.TWO_FA_STEPUP_SUCCESS,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="action",
        target_name=body.action,
        ip_address=_ip(request),
    )
    await db.commit()
    return StepUpResponse(authorized=True, stepup_token=stepup_token)


# ── GET /auth/2fa/report ──────────────────────────────────────────────────────

@router.get("/report", response_model=TwoFAStatusReport)
async def two_fa_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")

    from app.models.user import User as UserModel
    total_users_result = await db.execute(select(func.count()).select_from(UserModel))
    total_users = total_users_result.scalar_one()

    enabled_result = await db.execute(
        select(func.count()).where(User2FASettings.is_enabled == True)  # noqa: E712
    )
    enabled_count = enabled_result.scalar_one()

    method_breakdown = await tfa_crud.get_2fa_method_breakdown(db)
    failed_24h = await tfa_crud.count_failed_2fa_attempts_last_24h(db)

    return TwoFAStatusReport(
        total_users=total_users,
        users_with_2fa_enabled=enabled_count,
        users_without_2fa=total_users - enabled_count,
        method_breakdown={k.value if hasattr(k, 'value') else k: v for k, v in method_breakdown.items()},
        failed_attempts_last_24h=failed_24h,
    )


# ── AI: Security Risk Monitor ─────────────────────────────────────────────────

@router.get("/ai/security-risk")
async def ai_security_risk_monitor(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI Agent 1: Detect repeated failed 2FA attempts and suspicious patterns."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")

    from datetime import timedelta
    from app.models.two_factor import TwoFASession
    from sqlalchemy import desc

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await db.execute(
        select(
            TwoFASession.user_id,
            func.count().label("failed_count"),
        )
        .where(
            and_(
                TwoFASession.status == TwoFASessionStatus.FAILED,
                TwoFASession.created_at >= cutoff,
            )
        )
        .group_by(TwoFASession.user_id)
        .order_by(desc("failed_count"))
        .limit(20)
    )
    rows = result.all()

    risk_users = [
        {"user_id": str(r.user_id), "failed_attempts_24h": r.failed_count, "risk_level": "HIGH" if r.failed_count >= 3 else "MEDIUM"}
        for r in rows
    ]

    return {
        "agent": "Security Risk Monitor",
        "analysis_window_hours": 24,
        "high_risk_users": [u for u in risk_users if u["risk_level"] == "HIGH"],
        "medium_risk_users": [u for u in risk_users if u["risk_level"] == "MEDIUM"],
        "total_flagged": len(risk_users),
        "recommendation": "Review HIGH risk accounts for forced 2FA reset or temporary lockout.",
    }


# ── AI: Access Anomaly Detector ───────────────────────────────────────────────

@router.get("/ai/access-anomaly")
async def ai_access_anomaly_detector(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI Agent 2: Detect unusual access patterns (multiple IPs, rapid attempts)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")

    from datetime import timedelta
    from app.models.audit_log import AuditLog

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await db.execute(
        select(
            AuditLog.actor_id,
            AuditLog.ip_address,
            func.count().label("count"),
        )
        .where(
            and_(
                AuditLog.event_type.in_([
                    AuditEvent.TWO_FA_FAILED,
                    AuditEvent.LOGIN_FAILED,
                ]),
                AuditLog.created_at >= cutoff,
            )
        )
        .group_by(AuditLog.actor_id, AuditLog.ip_address)
        .order_by(desc("count"))
        .limit(50)
    )
    rows = result.all()

    # Group by actor, collect distinct IPs
    from collections import defaultdict
    actor_ips: dict = defaultdict(set)
    actor_attempts: dict = defaultdict(int)
    for row in rows:
        if row.actor_id:
            actor_ips[str(row.actor_id)].add(row.ip_address)
            actor_attempts[str(row.actor_id)] += row.count

    anomalies = [
        {
            "user_id": uid,
            "distinct_ips": len(ips),
            "total_failed_attempts": actor_attempts[uid],
            "ip_addresses": list(ips),
            "anomaly_type": "MULTI_IP" if len(ips) > 2 else "HIGH_FREQUENCY",
        }
        for uid, ips in actor_ips.items()
        if len(ips) > 1 or actor_attempts[uid] >= 5
    ]

    return {
        "agent": "Access Anomaly Detector",
        "analysis_window_hours": 24,
        "anomalies_detected": len(anomalies),
        "anomalies": anomalies,
        "recommendation": "Investigate multi-IP actors. Consider geo-blocking or forced re-auth.",
    }
