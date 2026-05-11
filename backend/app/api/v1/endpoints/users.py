from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, insert, select
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.core.password_policy import validate_password, PasswordPolicyError
from app.crud import user as crud
from app.crud import audit as audit_crud
from app.schemas.access_control import AccessScopeAssignList, AccessScopeRead
from app.schemas.user import UserCreate, UserUpdate, UserRead, UserReadShort, PasswordReset, RoleAssign
from app.schemas.common import PaginatedResponse
from app.models.audit_log import AuditEvent
from app.models.role import AccessScope

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
    try:
        validate_password(data.password, username=data.username)
    except PasswordPolicyError as e:
        raise HTTPException(status_code=422, detail={"error": "password_policy_violation", "violations": e.violations})
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
    try:
        validate_password(data.new_password, username=user.username)
    except PasswordPolicyError as e:
        raise HTTPException(status_code=422, detail={"error": "password_policy_violation", "violations": e.violations})
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


@router.get(
    "/{user_id}/scopes",
    response_model=List[AccessScopeRead],
    dependencies=[Depends(require_permission("users", "view"))],
)
async def list_user_scopes(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(
        select(AccessScope)
        .where(AccessScope.user_id == user_id)
        .order_by(AccessScope.scope_type, AccessScope.scope_name, AccessScope.scope_id)
    )
    return result.scalars().all()


@router.put(
    "/{user_id}/scopes",
    response_model=List[AccessScopeRead],
    dependencies=[Depends(require_permission("users", "manage"))],
)
async def assign_user_scopes(
    user_id: uuid.UUID,
    data: AccessScopeAssignList,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_result = await db.execute(select(AccessScope).where(AccessScope.user_id == user_id))
    old_scopes = old_result.scalars().all()
    old_keys = {(scope.scope_type, scope.scope_id) for scope in old_scopes}

    await db.execute(delete(AccessScope).where(AccessScope.user_id == user_id))
    rows = [
        {"id": uuid.uuid4(), "user_id": user_id, **scope.model_dump()}
        for scope in data.scopes
    ]
    if rows:
        await db.execute(insert(AccessScope), rows)

    new_keys = {(scope.scope_type, scope.scope_id) for scope in data.scopes}
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.USER_SCOPE_ASSIGNED if new_keys else AuditEvent.USER_SCOPE_REMOVED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(user.id),
        target_name=user.email,
        details={
            "added": sorted([f"{scope_type}:{scope_id}" for scope_type, scope_id in new_keys - old_keys]),
            "removed": sorted([f"{scope_type}:{scope_id}" for scope_type, scope_id in old_keys - new_keys]),
            "scope_count": len(rows),
        },
        ip_address=_ip(request),
    )
    await db.commit()

    result = await db.execute(
        select(AccessScope)
        .where(AccessScope.user_id == user_id)
        .order_by(AccessScope.scope_type, AccessScope.scope_name, AccessScope.scope_id)
    )
    return result.scalars().all()


# ── Self-service password change ─────────────────────────────────────────────

from pydantic import BaseModel as _BaseModel  # noqa: E402


class _ChangePasswordRequest(_BaseModel):
    current_password: str
    new_password: str


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_own_password(
    data: _ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Authenticated user changes their own password. Verifies current password first."""
    from app.core.security import verify_password

    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    try:
        validate_password(data.new_password, username=current_user.username)
    except PasswordPolicyError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": "password_policy_violation", "violations": e.violations},
        )

    await crud.reset_password(db, current_user, data.new_password)
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.PASSWORD_CHANGED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="user",
        target_id=str(current_user.id),
        target_name=current_user.email,
        ip_address=_ip(request),
    )
    await db.commit()
