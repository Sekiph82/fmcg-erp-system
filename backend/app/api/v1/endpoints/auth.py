import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud.user import authenticate, get_user_by_username
from app.crud import audit as audit_crud
from app.crud import two_factor as tfa_crud
from app.core.auth_cookies import (
    clear_auth_cookie,
    clear_refresh_cookie,
    set_auth_cookie,
    set_refresh_cookie,
)
from app.core.config import settings
from app.core.security import decode_access_token
from app.core.deps import get_current_user
from app.core.access_control import get_effective_modules, get_effective_scopes
from app.core import totp as totp_utils
from app.core import token_blocklist
from app.core.login_limiter import (
    check_login_allowed, record_login_failure, clear_login_failures,
)
from app.schemas.auth import LoginResponse
from app.schemas.user import UserRead
from app.models.audit_log import AuditEvent
from app.models.two_factor import TwoFAMethod
from app.services.auth_refresh_tokens import (
    InvalidRefreshToken,
    issue_auth_token_pair,
    refresh_family_for_token,
    revoke_all_user_sessions,
    revoke_refresh_family,
    rotate_refresh_token,
)

router = APIRouter()


def _ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate user",
    description=(
        "Authenticate with username and password. The access and refresh credentials are set as HttpOnly cookies. "
        "If 2FA is enabled, no credentials are issued until `POST /auth/2fa/login-verify` succeeds. "
        "Subject to IP and username rate limiting; repeated failures trigger a lock-out."
    ),
)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    ip = _ip(request)
    # Rate-limit by IP and username combination
    await check_login_allowed(form_data.username)
    if ip:
        await check_login_allowed(ip)

    user = await authenticate(db, form_data.username, form_data.password)
    if not user:
        existing = await get_user_by_username(db, form_data.username)
        failure_count = await record_login_failure(form_data.username)
        if ip:
            await record_login_failure(ip)

        await audit_crud.log_event(
            db,
            event_type=AuditEvent.LOGIN_FAILED,
            actor_id=existing.id if existing else None,
            actor_email=form_data.username,
            target_type="user",
            target_name=form_data.username,
            details={"reason": "bad_credentials", "failure_count": failure_count},
            ip_address=ip,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        await record_login_failure(form_data.username)
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.LOGIN_FAILED,
            actor_id=user.id,
            actor_email=user.email,
            target_type="user",
            target_id=str(user.id),
            target_name=user.email,
            details={"reason": "inactive_account"},
            ip_address=ip,
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    # Clear failure counter on successful credential validation
    clear_login_failures(form_data.username)
    if ip:
        clear_login_failures(ip)

    # ── 2FA check ─────────────────────────────────────────────────────────────
    tfa_settings = await tfa_crud.get_2fa_settings(db, user.id)
    if tfa_settings and tfa_settings.is_enabled:
        await tfa_crud.expire_old_sessions(db, user.id)

        challenge_code = None
        challenge_code_hash = None
        if tfa_settings.method in (TwoFAMethod.SMS, TwoFAMethod.EMAIL):
            challenge_code = totp_utils.generate_otp()
            challenge_code_hash = totp_utils.hash_otp(challenge_code)

        session = await tfa_crud.create_2fa_session(
            db,
            user_id=user.id,
            settings_id=tfa_settings.id,
            method=tfa_settings.method,
            challenge_code=challenge_code_hash,
        )
        await db.commit()

        # Dispatch OTP after commit so session is durable before sending
        if challenge_code:
            from app.services.email_sender import send_otp_email
            from app.services.sms_sender import send_otp_sms
            try:
                if tfa_settings.method == TwoFAMethod.EMAIL:
                    dest = tfa_settings.email or user.email
                    await send_otp_email(dest, challenge_code)
                else:
                    await send_otp_sms(tfa_settings.phone_number, challenge_code)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error(
                    "OTP dispatch failed for user %s method=%s: %s",
                    user.id, tfa_settings.method, exc,
                )
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.TWO_FA_CHALLENGE_SENT,
            actor_id=user.id,
            actor_email=user.email,
            target_type="user",
            target_id=str(user.id),
            target_name=user.email,
            details={"method": tfa_settings.method},
            ip_address=ip,
        )
        await db.commit()

        pending_token = totp_utils.create_pending_2fa_token(str(user.id), str(session.id))
        return LoginResponse(
            two_fa_required=True,
            session_token=pending_token,
            method=tfa_settings.method,
        )

    await audit_crud.log_event(
        db,
        event_type=AuditEvent.LOGIN_SUCCESS,
        actor_id=user.id,
        actor_email=user.email,
        target_type="user",
        target_id=str(user.id),
        target_name=user.email,
        ip_address=ip,
    )
    token_pair = await issue_auth_token_pair(db, user.id)
    await db.commit()
    set_auth_cookie(response, token_pair.access_token)
    set_refresh_cookie(response, token_pair.refresh_token)
    return LoginResponse(
        access_token=token_pair.access_token if settings.AUTH_RETURN_TOKEN_IN_BODY else None,
        must_change_password=bool(getattr(user, "must_change_password", False)),
    )


@router.post("/logout", summary="Revoke session", description="Revokes the refresh-token family and current access token, then clears both authentication cookies.")
async def logout(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invalidate the current JWT by adding it to the blocklist."""
    from datetime import datetime, timezone, timedelta

    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    payload = decode_access_token(token) if token else None
    family_id = None
    if payload and payload.get("sid"):
        try:
            family_id = uuid.UUID(str(payload["sid"]))
        except (ValueError, TypeError, AttributeError):
            family_id = None
    if family_id is None:
        refresh_cookie = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if refresh_cookie:
            family_id = await refresh_family_for_token(db, refresh_cookie, current_user.id)
    await revoke_refresh_family(
        db,
        family_id=family_id,
        user_id=current_user.id,
    )
    if token:
        expire_at = (
            datetime.now(timezone.utc) +
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        ).timestamp()
        await token_blocklist.add(token, expire_at)
    clear_auth_cookie(response)
    clear_refresh_cookie(response)

    await audit_crud.log_event(
        db,
        event_type=AuditEvent.LOGOUT,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(current_user.id),
        target_name=current_user.email,
        ip_address=_ip(request),
    )
    await db.commit()
    return {"detail": "Logged out successfully"}


@router.post(
    "/logout-all",
    summary="Revoke all sessions",
    description="Revokes every refresh session and invalidates all access tokens for the authenticated user.",
)
async def logout_all_sessions(
    response: Response,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    revoked_count = await revoke_all_user_sessions(db, current_user.id)
    await db.commit()
    clear_auth_cookie(response)
    clear_refresh_cookie(response)
    return {"detail": "All sessions revoked successfully", "refresh_tokens_revoked": revoked_count}


@router.post(
    "/refresh",
    summary="Rotate the current refresh token",
    description="Consumes the HttpOnly refresh cookie and issues a new access/refresh pair. Reuse revokes the session family.",
)
async def refresh_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if not raw_token:
        clear_auth_cookie(response)
        clear_refresh_cookie(response)
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"detail": "Refresh session is unavailable. Please log in again."}

    try:
        token_pair, _user = await rotate_refresh_token(db, raw_token)
        await db.commit()
    except InvalidRefreshToken:
        clear_auth_cookie(response)
        clear_refresh_cookie(response)
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"detail": "Refresh session is invalid, expired, or revoked. Please log in again."}

    set_auth_cookie(response, token_pair.access_token)
    set_refresh_cookie(response, token_pair.refresh_token)
    return {
        "access_token": token_pair.access_token if settings.AUTH_RETURN_TOKEN_IN_BODY else None,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserRead, summary="Current user profile", description="Returns the authenticated user's profile, roles, permission codes, effective modules, and access scopes. Use this to bootstrap frontend auth context.")
async def get_me(current_user=Depends(get_current_user)):
    payload = UserRead.model_validate(current_user).model_dump()
    payload["modules"] = get_effective_modules(current_user)
    payload["scopes"] = get_effective_scopes(current_user)
    payload["feature_flags"] = {}
    return payload
