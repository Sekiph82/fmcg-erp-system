from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud.user import authenticate, get_user_by_username
from app.crud import audit as audit_crud
from app.crud import two_factor as tfa_crud
from app.core.auth_cookies import clear_auth_cookie, set_auth_cookie
from app.core.config import settings
from app.core.security import create_access_token
from app.core.deps import get_current_user
from app.core.access_control import get_effective_modules, get_effective_scopes
from app.core import totp as totp_utils
from app.core import token_blocklist
from app.core.login_limiter import (
    check_login_allowed, record_login_failure, clear_login_failures,
)
from app.schemas.auth import Token, LoginResponse
from app.schemas.user import UserRead
from app.models.audit_log import AuditEvent
from app.models.two_factor import TwoFAMethod

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
        "Authenticate with username and password. Returns a JWT access token and user profile. "
        "If 2FA is enabled the response instead returns a `tfa_session_id` — "
        "pass this to `POST /auth/2fa/verify` to complete login. "
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
        if tfa_settings.method in (TwoFAMethod.SMS, TwoFAMethod.EMAIL):
            challenge_code = totp_utils.generate_otp()
            # TODO: dispatch OTP via notification service

        session = await tfa_crud.create_2fa_session(
            db,
            user_id=user.id,
            settings_id=tfa_settings.id,
            method=tfa_settings.method,
            challenge_code=challenge_code,
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
    await db.commit()
    access_token = create_access_token(str(user.id))
    set_auth_cookie(response, access_token)
    return LoginResponse(
        access_token=access_token if settings.AUTH_RETURN_TOKEN_IN_BODY else None,
        must_change_password=bool(getattr(user, "must_change_password", False)),
    )


@router.post("/logout", summary="Revoke access token", description="Adds the current JWT to the token blocklist. The token is invalid for all subsequent requests until it expires naturally.")
async def logout(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invalidate the current JWT by adding it to the blocklist."""
    from datetime import datetime, timezone, timedelta

    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if token:
        expire_at = (
            datetime.now(timezone.utc) +
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        ).timestamp()
        await token_blocklist.add(token, expire_at)
    clear_auth_cookie(response)

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


@router.get("/me", response_model=UserRead, summary="Current user profile", description="Returns the authenticated user's profile, roles, permission codes, effective modules, and access scopes. Use this to bootstrap frontend auth context.")
async def get_me(current_user=Depends(get_current_user)):
    payload = UserRead.model_validate(current_user).model_dump()
    payload["modules"] = get_effective_modules(current_user)
    payload["scopes"] = get_effective_scopes(current_user)
    payload["feature_flags"] = {}
    return payload
