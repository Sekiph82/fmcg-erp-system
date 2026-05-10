from fastapi import APIRouter, Depends

from app.core.deps import require_permission
from app.core.module_registry import module_manifest, registry_permission_codes

router = APIRouter()


@router.get("/manifest", dependencies=[Depends(require_permission("roles", "view"))])
async def get_module_manifest():
    """Return backend-owned module metadata for route, permission, sidebar, and AI visibility."""
    return {
        "modules": module_manifest(),
        "permission_codes": sorted(registry_permission_codes()),
    }
