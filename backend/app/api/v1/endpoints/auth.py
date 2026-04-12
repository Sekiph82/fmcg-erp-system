from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud.user import authenticate, get_user_by_username
from app.crud import audit as audit_crud
from app.core.security import create_access_token
from app.core.deps import get_current_user
from app.schemas.auth import Token
from app.schemas.user import UserRead
from app.models.audit_log import AuditEvent

router = APIRouter()


def _ip(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate(db, form_data.username, form_data.password)
    if not user:
        existing = await get_user_by_username(db, form_data.username)
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.LOGIN_FAILED,
            actor_id=existing.id if existing else None,
            actor_email=form_data.username,
            target_type="user",
            target_name=form_data.username,
            details={"reason": "bad_credentials"},
            ip_address=_ip(request),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.LOGIN_FAILED,
            actor_id=user.id,
            actor_email=user.email,
            target_type="user",
            target_id=str(user.id),
            target_name=user.email,
            details={"reason": "inactive_account"},
            ip_address=_ip(request),
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    await audit_crud.log_event(
        db,
        event_type=AuditEvent.LOGIN_SUCCESS,
        actor_id=user.id,
        actor_email=user.email,
        target_type="user",
        target_id=str(user.id),
        target_name=user.email,
        ip_address=_ip(request),
    )
    await db.commit()
    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserRead)
async def get_me(current_user=Depends(get_current_user)):
    return current_user
