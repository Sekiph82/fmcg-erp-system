"""E-mail engagement and sales activity analytics (M43.S01.T006). Prefix /api/v1/crm-engagement.
Company-wide CRM viewers see every sender; others see only the e-mail they sent themselves."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_control import has_permission, require_any_permission
from app.core.deps import get_current_user, get_db
from app.services import crm_engagement_service as engagement

router = APIRouter()


@router.get("", dependencies=[Depends(require_any_permission(("crm.view", "crm.view_all")))])
async def engagement_summary(days: int = Query(30, ge=1, le=365), db: AsyncSession = Depends(get_db),
                             current_user=Depends(get_current_user)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    everyone = current_user.is_superuser or has_permission(current_user, "crm.view_all")
    return await engagement.analytics(db, since=since, created_by=None if everyone else current_user.username)
