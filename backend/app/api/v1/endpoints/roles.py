from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from app.db.session import get_db
from app.core.deps import get_current_user, require_permission
from app.crud import role as crud
from app.crud import audit as audit_crud
from app.schemas.role import (
    RoleCreate, RoleUpdate, RoleRead, RoleReadShort,
    PermissionCreate, PermissionRead, PermissionAssign,
)
from app.models.audit_log import AuditEvent

router = APIRouter()


def _ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )


# ── Permissions ────────────────────────────────────────────────────────────────

@router.get(
    "/permissions",
    response_model=List[PermissionRead],
    dependencies=[Depends(require_permission("roles", "view"))],
)
async def list_permissions(
    module: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_permissions(db, module=module)


@router.post(
    "/permissions",
    response_model=PermissionRead,
    status_code=201,
    dependencies=[Depends(require_permission("roles", "create"))],
)
async def create_permission(data: PermissionCreate, db: AsyncSession = Depends(get_db)):
    existing = await crud.get_permission_by_code(db, data.code)
    if existing:
        raise HTTPException(status_code=400, detail="Permission code already exists")
    perm = await crud.create_permission(db, data)
    await db.commit()
    return perm


# ── Roles ──────────────────────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[RoleRead],
    dependencies=[Depends(require_permission("roles", "view"))],
)
async def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await crud.list_roles(db, skip=skip, limit=limit, is_active=is_active)


@router.post(
    "/",
    response_model=RoleRead,
    status_code=201,
    dependencies=[Depends(require_permission("roles", "create"))],
)
async def create_role(
    data: RoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = await crud.get_role_by_name(db, data.name)
    if existing:
        raise HTTPException(status_code=400, detail="Role name already exists")
    role = await crud.create_role(db, data)
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.ROLE_CREATED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="role",
        target_id=str(role.id),
        target_name=role.name,
        ip_address=_ip(request),
    )
    await db.commit()
    return role


@router.get(
    "/{role_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_permission("roles", "view"))],
)
async def get_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    role = await crud.get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.patch(
    "/{role_id}",
    response_model=RoleRead,
    dependencies=[Depends(require_permission("roles", "edit"))],
)
async def update_role(
    role_id: uuid.UUID,
    data: RoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = await crud.get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    role = await crud.update_role(db, role, data)
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.ROLE_UPDATED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="role",
        target_id=str(role.id),
        target_name=role.name,
        ip_address=_ip(request),
    )
    await db.commit()
    return role


@router.post(
    "/{role_id}/activate",
    response_model=RoleRead,
    dependencies=[Depends(require_permission("roles", "edit"))],
)
async def activate_role(
    role_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = await crud.get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    role.is_active = True
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.ROLE_ACTIVATED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="role",
        target_id=str(role.id),
        target_name=role.name,
        ip_address=_ip(request),
    )
    await db.commit()
    return role


@router.post(
    "/{role_id}/deactivate",
    response_model=RoleRead,
    dependencies=[Depends(require_permission("roles", "edit"))],
)
async def deactivate_role(
    role_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = await crud.get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.name == "owner":
        raise HTTPException(status_code=400, detail="Cannot deactivate the owner role")
    role.is_active = False
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.ROLE_DEACTIVATED,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target_type="role",
        target_id=str(role.id),
        target_name=role.name,
        ip_address=_ip(request),
    )
    await db.commit()
    return role


@router.put(
    "/{role_id}/permissions",
    response_model=RoleRead,
    dependencies=[Depends(require_permission("roles", "edit"))],
)
async def assign_permissions(
    role_id: uuid.UUID,
    data: PermissionAssign,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = await crud.get_role(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    old_perm_ids = {str(p.id) for p in role.permissions}
    role = await crud.set_role_permissions(db, role, data.permission_ids)
    new_perm_ids = {str(p.id) for p in role.permissions}
    added = new_perm_ids - old_perm_ids
    removed = old_perm_ids - new_perm_ids
    if added or removed:
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.ROLE_PERMISSION_ASSIGNED if added else AuditEvent.ROLE_PERMISSION_REMOVED,
            actor_id=current_user.id,
            actor_email=current_user.email,
            target_type="role",
            target_id=str(role.id),
            target_name=role.name,
            details={"added": list(added), "removed": list(removed)},
            ip_address=_ip(request),
        )
    await db.commit()
    return role
