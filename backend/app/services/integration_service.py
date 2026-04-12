"""
Base integration service: unified logging and config helpers.
All provider-specific services import and use log_call() for traceability.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrations import (
    IntegrationConfig, IntegrationLog, IntegrationProvider,
    IntegrationLogStatus, IntegrationStatus,
)


async def log_call(
    db: AsyncSession,
    *,
    provider: IntegrationProvider,
    integration_type: str,
    endpoint: Optional[str] = None,
    request_payload: Optional[Dict[str, Any]] = None,
    response_payload: Optional[Dict[str, Any]] = None,
    status: IntegrationLogStatus = IntegrationLogStatus.SUCCESS,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
    reference: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    retry_count: int = 0,
) -> IntegrationLog:
    """Write one integration audit log row. Call at every external API boundary."""

    def _sanitise(payload: Optional[Dict[str, Any]]) -> Optional[str]:
        if payload is None:
            return None
        # Mask sensitive keys
        sensitive = {"Password", "ConsumerSecret", "ConsumerKey", "access_token",
                     "token", "secret", "key", "passkey"}
        clean = {
            k: ("***" if any(s.lower() in k.lower() for s in sensitive) else v)
            for k, v in payload.items()
        }
        return json.dumps(clean)

    log = IntegrationLog(
        provider=provider,
        integration_type=integration_type,
        endpoint=endpoint,
        request_payload=_sanitise(request_payload),
        response_payload=json.dumps(response_payload) if response_payload else None,
        status=status,
        error_message=error_message,
        duration_ms=duration_ms,
        reference=reference,
        idempotency_key=idempotency_key,
        retry_count=retry_count,
    )
    db.add(log)
    await db.flush()
    return log


async def get_config(
    db: AsyncSession,
    provider: IntegrationProvider,
) -> Optional[IntegrationConfig]:
    result = await db.execute(
        select(IntegrationConfig)
        .where(
            and_(
                IntegrationConfig.provider == provider,
                IntegrationConfig.is_active == True,
            )
        )
        .order_by(IntegrationConfig.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_configs(db: AsyncSession) -> List[IntegrationConfig]:
    result = await db.execute(
        select(IntegrationConfig).order_by(IntegrationConfig.provider, IntegrationConfig.name)
    )
    return list(result.scalars().all())


async def create_config(db: AsyncSession, data: dict) -> IntegrationConfig:
    cfg = IntegrationConfig(**data)
    db.add(cfg)
    await db.flush()
    await db.refresh(cfg)
    return cfg


async def update_config(db: AsyncSession, cfg: IntegrationConfig, data: dict) -> IntegrationConfig:
    for k, v in data.items():
        setattr(cfg, k, v)
    await db.flush()
    await db.refresh(cfg)
    return cfg


async def list_logs(
    db: AsyncSession,
    provider: Optional[IntegrationProvider] = None,
    status: Optional[IntegrationLogStatus] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[IntegrationLog]:
    q = select(IntegrationLog).order_by(IntegrationLog.created_at.desc())
    if provider:
        q = q.where(IntegrationLog.provider == provider)
    if status:
        q = q.where(IntegrationLog.status == status)
    result = await db.execute(q.limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_provider_stats(
    db: AsyncSession,
    provider: IntegrationProvider,
    hours: int = 24,
) -> Dict[str, int]:
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = (
        select(IntegrationLog.status, func.count(IntegrationLog.id))
        .where(
            and_(
                IntegrationLog.provider == provider,
                IntegrationLog.created_at >= since,
            )
        )
        .group_by(IntegrationLog.status)
    )
    result = await db.execute(q)
    stats = {r[0]: r[1] for r in result}
    return {
        "success": stats.get(IntegrationLogStatus.SUCCESS, 0),
        "failed": stats.get(IntegrationLogStatus.FAILED, 0),
        "pending": stats.get(IntegrationLogStatus.PENDING, 0),
    }
