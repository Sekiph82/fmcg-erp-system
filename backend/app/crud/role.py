from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid

from app.models.role import Role, Permission
from app.schemas.role import RoleCreate, RoleUpdate, PermissionCreate


async def get_role(db: AsyncSession, role_id: uuid.UUID) -> Optional[Role]:
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    return result.scalar_one_or_none()


async def get_role_by_name(db: AsyncSession, name: str) -> Optional[Role]:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()


async def list_roles(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    is_active: Optional[bool] = None,
) -> List[Role]:
    q = select(Role).options(selectinload(Role.permissions))
    if is_active is not None:
        q = q.where(Role.is_active == is_active)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_role(db: AsyncSession, data: RoleCreate) -> Role:
    role = Role(name=data.name, description=data.description)
    if data.permission_ids:
        perms = await db.execute(select(Permission).where(Permission.id.in_(data.permission_ids)))
        role.permissions = list(perms.scalars().all())
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


async def update_role(db: AsyncSession, role: Role, data: RoleUpdate) -> Role:
    update_data = data.model_dump(exclude_unset=True)
    if "permission_ids" in update_data:
        perm_ids = update_data.pop("permission_ids")
        perms = await db.execute(select(Permission).where(Permission.id.in_(perm_ids)))
        role.permissions = list(perms.scalars().all())
    for key, value in update_data.items():
        setattr(role, key, value)
    await db.flush()
    await db.refresh(role)
    return role


async def set_role_permissions(db: AsyncSession, role: Role, permission_ids: List[uuid.UUID]) -> Role:
    perms = await db.execute(select(Permission).where(Permission.id.in_(permission_ids)))
    role.permissions = list(perms.scalars().all())
    await db.flush()
    await db.refresh(role)
    return role


async def list_permissions(
    db: AsyncSession,
    *,
    module: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> List[Permission]:
    q = select(Permission)
    if module:
        q = q.where(Permission.module == module)
    result = await db.execute(q.order_by(Permission.module, Permission.action).offset(offset).limit(min(limit, 1000)))
    return list(result.scalars().all())


async def get_permission_by_code(db: AsyncSession, code: str) -> Optional[Permission]:
    result = await db.execute(select(Permission).where(Permission.code == code))
    return result.scalar_one_or_none()


async def create_permission(db: AsyncSession, data: PermissionCreate) -> Permission:
    perm = Permission(**data.model_dump())
    db.add(perm)
    await db.flush()
    await db.refresh(perm)
    return perm
