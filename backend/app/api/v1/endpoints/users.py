from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import user as crud
from app.crud import audit as audit_crud
from app.schemas.user import UserCreate, UserUpdate, UserRead, UserReadShort, PasswordReset, RoleAssign
from app.schemas.common import PaginatedResponse
from app.models.audit_log import AuditEvent

router = APIRouter()


def _ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )


@router.get("/me", response_model=UserRead)
async def read_me(current_user=Depends(get_current_user)):
    return current_user


@router.get(
    "/",
    response_model=PaginatedResponse[UserReadShort],
    dependencies=[Depends(require_permission("users", "view"))],
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    role_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    users = await crud.list_users(db, skip=skip, limit=limit,
                                   search=search, is_active=is_active, role_id=role_id)
    total = await crud.count_users(db, search=search, is_active=is_active, role_id=role_id)
    return PaginatedResponse(total=total, page=skip // limit + 1, page_size=limit, items=users)


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users", "create"))],
)
async def create_user(
    data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if await crud.get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await crud.get_user_by_username(db, data.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    user = await crud.create_user(db, data)
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.USER_CREATED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(user.id),
        target_name=user.email,
        ip_address=_ip(request),
    )
    await db.commit()
    return user


@router.get(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission("users", "view"))],
)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_permission("users", "edit"))],
)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user = await crud.update_user(db, user, data)
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.USER_UPDATED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(user.id),
        target_name=user.email,
        ip_address=_ip(request),
    )
    await db.commit()
    return user


@router.post(
    "/{user_id}/activate",
    response_model=UserRead,
    dependencies=[Depends(require_permission("users", "edit"))],
)
async def activate_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.USER_ACTIVATED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(user.id),
        target_name=user.email,
        ip_address=_ip(request),
    )
    await db.commit()
    return user


@router.post(
    "/{user_id}/deactivate",
    response_model=UserRead,
    dependencies=[Depends(require_permission("users", "edit"))],
)
async def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user.is_active = False
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.USER_DEACTIVATED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(user.id),
        target_name=user.email,
        ip_address=_ip(request),
    )
    await db.commit()
    return user


@router.post(
    "/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("users", "edit"))],
)
async def reset_password(
    user_id: uuid.UUID,
    data: PasswordReset,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await crud.reset_password(db, user, data.new_password)
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.PASSWORD_RESET,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(user.id),
        target_name=user.email,
        ip_address=_ip(request),
    )
    await db.commit()


@router.put(
    "/{user_id}/roles",
    response_model=UserRead,
    dependencies=[Depends(require_permission("users", "edit"))],
)
async def assign_roles(
    user_id: uuid.UUID,
    data: RoleAssign,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    old_role_ids = {str(r.id) for r in user.roles}
    user = await crud.set_user_roles(db, user, data.role_ids)
    new_role_ids = {str(r.id) for r in user.roles}

    added = new_role_ids - old_role_ids
    removed = old_role_ids - new_role_ids
    if added:
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.USER_ROLE_ASSIGNED,
            actor_id=current_user.id,
            actor_email=current_user.email,
            target_type="user",
            target_id=str(user.id),
            target_name=user.email,
            details={"added_role_ids": list(added)},
            ip_address=_ip(request),
        )
    if removed:
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.USER_ROLE_REMOVED,
            actor_id=current_user.id,
            actor_email=current_user.email,
            target_type="user",
            target_id=str(user.id),
            target_name=user.email,
            details={"removed_role_ids": list(removed)},
            ip_address=_ip(request),
        )
    await db.commit()
    return user
