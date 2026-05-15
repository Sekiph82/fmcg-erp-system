from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.role import Permission
from app.core.access_control import get_effective_permission_codes
from app.core.module_registry import (
    covered_registry_permission_codes,
    module_manifest,
    permission_coverage_report,
    permission_is_covered,
    registry_permission_codes,
)

router = APIRouter()


def _user_permission_codes(user, all_codes: set[str]) -> set[str]:
    if getattr(user, "is_superuser", False):
        return all_codes
    return set(get_effective_permission_codes(user))


async def _all_permission_codes(db: AsyncSession) -> set[str]:
    result = await db.execute(select(Permission.code))
    codes = set(result.scalars().all())
    return codes | registry_permission_codes()


async def _database_permission_codes(db: AsyncSession) -> set[str]:
    result = await db.execute(select(Permission.code))
    return set(result.scalars().all())


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
        if any(permission_is_covered(code, user_codes) for code in module["permission_codes"])
    ]
    visible_registry_codes = covered_registry_permission_codes(user_codes)
    return {
        "modules": modules,
        "permission_codes": sorted(all_codes),
        "visible_permission_codes": sorted((user_codes & all_codes) | visible_registry_codes),
    }


@router.get("/permissions/coverage", dependencies=[Depends(require_permission("roles", "view"))])
async def get_permission_coverage(
    db: AsyncSession = Depends(get_db),
):
    """Return registry/database permission drift details for admin review."""
    registry_codes = registry_permission_codes()
    database_codes = await _database_permission_codes(db)
    coverage = permission_coverage_report(registry_codes, database_codes)

    return {
        "registry_permission_count": len(registry_codes),
        "database_permission_count": len(database_codes),
        "covered_registry_permissions": coverage["covered"],
        "missing_registry_permissions": coverage["missing"],
        "database_only_permissions": sorted(database_codes - registry_codes),
    }
