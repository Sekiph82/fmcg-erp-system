from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid

from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def list_users(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    role_id: Optional[uuid.UUID] = None,
) -> List[User]:
    q = (
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .distinct()
    )
    if search:
        pattern = f"%{search}%"
        q = q.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.username.ilike(pattern),
            )
        )
    if is_active is not None:
        q = q.where(User.is_active == is_active)
    if role_id:
        q = q.join(User.roles).where(Role.id == role_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return list(result.scalars().all())


async def count_users(
    db: AsyncSession,
    *,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    role_id: Optional[uuid.UUID] = None,
) -> int:
    q = select(func.count(User.id.distinct()))
    if search:
        pattern = f"%{search}%"
        q = q.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.username.ilike(pattern),
            )
        )
    if is_active is not None:
        q = q.where(User.is_active == is_active)
    if role_id:
        q = q.select_from(User).join(User.roles).where(Role.id == role_id)
    result = await db.execute(q)
    return result.scalar_one()


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        is_active=data.is_active,
        is_superuser=data.is_superuser,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    update_data = data.model_dump(exclude_unset=True)
    if "password" in update_data:
        user.hashed_password = hash_password(update_data.pop("password"))
    if "role_ids" in update_data:
        role_ids = update_data.pop("role_ids")
        roles_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
        user.roles = list(roles_result.scalars().all())
    for key, value in update_data.items():
        setattr(user, key, value)
    await db.flush()
    await db.refresh(user)
    return user


async def set_user_roles(db: AsyncSession, user: User, role_ids: List[uuid.UUID]) -> User:
    roles_result = await db.execute(select(Role).where(Role.id.in_(role_ids)))
    user.roles = list(roles_result.scalars().all())
    await db.flush()
    await db.refresh(user)
    return user


async def reset_password(db: AsyncSession, user: User, new_password: str) -> None:
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    await db.flush()


async def authenticate(db: AsyncSession, username: str, password: str) -> Optional[User]:
    from app.core.security import verify_password
    user = await get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
