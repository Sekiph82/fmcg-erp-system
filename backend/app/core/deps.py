import logging
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid

from app.core.config import settings
from app.core.security import decode_token
from app.core import token_blocklist
from app.db.session import get_db

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User
    from app.models.role import Role

    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    # Reject explicitly logged-out tokens
    if await token_blocklist.is_blocked(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked. Please log in again.")

    user_id = decode_token(token)
    if not user_id:
        logger.warning("Auth failed: invalid or expired token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        result = await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == uuid.UUID(user_id))
        )
    except Exception:
        logger.exception("Auth failed: database error looking up user_id=%s", user_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication error")
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("Auth failed: user_id=%s not found", user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    if not user.is_active:
        logger.warning("Auth failed: user_id=%s is inactive", user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


async def get_current_active_superuser(current_user=Depends(get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user


def require_permission(module: str, action: str):
    """
    Returns a dependency that grants access when the user is superuser
    OR holds a role that includes the '{module}.{action}' permission.
    """
    permission_code = f"{module}.{action}"

    async def _check(current_user=Depends(get_current_user)):
        if current_user.is_superuser:
            return current_user
        user_permissions = {
            perm.code
            for role in current_user.roles
            if role.is_active
            for perm in role.permissions
        }
        if permission_code not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_code}' required",
            )
        return current_user

    return _check
