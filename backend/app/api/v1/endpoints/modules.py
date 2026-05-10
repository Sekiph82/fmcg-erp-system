from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.role import Permission
from app.core.module_registry import module_manifest, registry_permission_codes

router = APIRouter()


def _user_permission_codes(user, all_codes: set[str]) -> set[str]:
    if getattr(user, "is_superuser", False):
        return all_codes
    return {
        perm.code
        for role in getattr(user, "roles", [])
        if getattr(role, "is_active", False)
        for perm in getattr(role, "permissions", [])
    }


async def _all_permission_codes(db: AsyncSession) -> set[str]:
    result = await db.execute(select(Permission.code))
    codes = set(result.scalars().all())
    return codes | registry_permission_codes()


@router.get("/manifest")
async def get_module_manifest(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return backend-owned module metadata visible to the current user."""
    all_codes = await _all_permission_codes(db)
    user_codes = _user_permission_codes(current_user, all_codes)
    modules = [
        module
        for module in module_manifest()
        if any(code in user_codes for code in module["permission_codes"])
    ]
    return {
        "modules": modules,
        "permission_codes": sorted(all_codes),
        "visible_permission_codes": sorted(user_codes & all_codes),
    }
