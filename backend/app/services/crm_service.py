"""
CRM Integration Service — scalable placeholder.

Implements the synchronization contract between internal Customer records
and external CRM systems (Salesforce, HubSpot, Zoho, etc.).

To activate a CRM:
  1. Add an IntegrationConfig record with provider=CRM, settings_json containing
     {"provider_name": "hubspot", "api_key": "...", "portal_id": "..."}
  2. Implement _push_to_crm() / _pull_from_crm() with provider-specific HTTP calls.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrations import (
    CrmCustomerMapping, SyncStatus,
    IntegrationProvider, IntegrationLogStatus,
)
from app.models.sales import Customer
from app.services import integration_service as log_svc

logger = logging.getLogger(__name__)


async def sync_customers(
    db: AsyncSession,
    direction: str = "PUSH",
    customer_ids: Optional[List[str]] = None,
    crm_provider: str = "generic",
) -> Tuple[int, int, List[str]]:
    """
    Synchronise Customer records with the external CRM.
    Returns (total, synced_count, error_list).

    PLACEHOLDER: logs intent, creates/updates CrmCustomerMapping records,
    but does not call a live CRM API yet.
    """
    # Load customers
    q = select(Customer).where(Customer.is_active == True)
    if customer_ids:
        import uuid
        q = q.where(Customer.id.in_([uuid.UUID(c) for c in customer_ids]))
    result = await db.execute(q)
    customers = list(result.scalars().all())

    synced = 0
    errors: List[str] = []

    for customer in customers:
        try:
            # Upsert mapping record
            existing = await db.execute(
                select(CrmCustomerMapping).where(
                    CrmCustomerMapping.customer_id == customer.id,
                    CrmCustomerMapping.crm_provider == crm_provider,
                )
            )
            mapping = existing.scalar_one_or_none()

            if not mapping:
                # PLACEHOLDER: would call CRM API to create contact
                external_id = f"CRM-{str(customer.id)[:8].upper()}"
                mapping = CrmCustomerMapping(
                    customer_id=customer.id,
                    crm_provider=crm_provider,
                    external_crm_id=external_id,
                    sync_status=SyncStatus.SYNCED,
                    sync_direction=direction,
                    last_sync_at=datetime.now(timezone.utc),
                    metadata_json=json.dumps({
                        "name": customer.name,
                        "email": customer.email,
                        "channel": str(customer.channel) if customer.channel else None,
                    }),
                )
                db.add(mapping)
            else:
                # PLACEHOLDER: would call CRM API to update contact
                mapping.sync_status = SyncStatus.SYNCED
                mapping.last_sync_at = datetime.now(timezone.utc)

            await db.flush()
            synced += 1
        except Exception as exc:
            logger.error("CRM sync error for customer %s: %s", customer.id, exc)
            errors.append(f"{customer.code}: {exc}")

    await log_svc.log_call(
        db,
        provider=IntegrationProvider.CRM,
        integration_type="SYNC",
        endpoint=f"crm/{crm_provider}/customers",
        request_payload={"direction": direction, "count": len(customers)},
        response_payload={"synced": synced, "errors": len(errors)},
        status=IntegrationLogStatus.SUCCESS if not errors else IntegrationLogStatus.FAILED,
        error_message="; ".join(errors[:5]) if errors else None,
    )

    await db.flush()
    return len(customers), synced, errors


async def list_mappings(db: AsyncSession, limit: int = 100) -> List[CrmCustomerMapping]:
    result = await db.execute(
        select(CrmCustomerMapping).order_by(CrmCustomerMapping.last_sync_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
