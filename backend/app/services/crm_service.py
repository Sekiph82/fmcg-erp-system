"""
External CRM integration (Salesforce, HubSpot, Zoho, ...).

No vendor connector is implemented yet, so customers are never pushed or pulled. The
earlier placeholder invented external IDs and marked mappings SYNCED without contacting
any CRM; that fabricated integration data and was removed. A connector must implement
real provider calls before ``/integrations/crm/sync/customers`` can succeed.
"""
from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrations import CrmCustomerMapping


async def list_mappings(db: AsyncSession, limit: int = 100) -> List[CrmCustomerMapping]:
    result = await db.execute(
        select(CrmCustomerMapping).order_by(CrmCustomerMapping.last_sync_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
