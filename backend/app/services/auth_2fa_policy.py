"""Shared policy for accounts that must use two-factor authentication."""
from uuid import UUID

from sqlalchemy import exists, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Permission, Role, role_permission
from app.models.user import User, user_role


async def requires_privileged_2fa(db: AsyncSession, user_id: UUID | str) -> bool:
    """Require 2FA for system administrators and every role with finance access."""
    user_id = UUID(str(user_id))
    privileged_role = exists(
        select(Role.id)
        .select_from(user_role.join(Role, user_role.c.role_id == Role.id))
        .where(
            user_role.c.user_id == user_id,
            Role.is_active.is_(True),
            Role.name.in_(("owner", "admin")),
        )
    )
    finance_permission = exists(
        select(Permission.id)
        .select_from(
            user_role.join(Role, user_role.c.role_id == Role.id)
            .join(role_permission, role_permission.c.role_id == Role.id)
            .join(Permission, Permission.id == role_permission.c.permission_id)
        )
        .where(
            user_role.c.user_id == user_id,
            Role.is_active.is_(True),
            Permission.is_active.is_(True),
            Permission.module == "finance",
        )
    )
    query = select(
        exists(
            select(User.id).where(
                User.id == user_id,
                or_(User.is_superuser.is_(True), privileged_role, finance_permission),
            )
        )
    )
    return bool(await db.scalar(query))
