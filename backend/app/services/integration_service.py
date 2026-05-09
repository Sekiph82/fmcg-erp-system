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

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integrations import (
    IntegrationConfig, IntegrationLog, IntegrationProvider,
    IntegrationLogStatus, IntegrationStatus,
    ConnectorRegistry, ConnectorStatus, PluginInstallation,
    PluginInstallStatus, PluginLifecycleEvent, PluginLifecycleAction,
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


def _loads_list(value: Optional[str]) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _dumps_config(value: Optional[Dict[str, Any]]) -> Optional[str]:
    if value is None:
        return None
    sensitive = {"password", "secret", "token", "key", "client_secret", "consumer_secret"}
    clean = {
        k: ("***" if any(s in k.lower() for s in sensitive) else v)
        for k, v in value.items()
    }
    return json.dumps(clean)


async def get_connector(db: AsyncSession, connector_code: str) -> ConnectorRegistry:
    result = await db.execute(
        select(ConnectorRegistry).where(ConnectorRegistry.connector_code == connector_code)
    )
    connector = result.scalar_one_or_none()
    if not connector:
        from fastapi import HTTPException
        raise HTTPException(404, f"Connector '{connector_code}' not found in registry")
    return connector


async def get_installation(
    db: AsyncSession,
    connector_code: str,
    tenant_key: str = "default",
) -> Optional[PluginInstallation]:
    result = await db.execute(
        select(PluginInstallation).where(
            PluginInstallation.connector_code == connector_code,
            PluginInstallation.tenant_key == tenant_key,
        )
    )
    return result.scalar_one_or_none()


async def list_installations(
    db: AsyncSession,
    tenant_key: Optional[str] = None,
    status: Optional[PluginInstallStatus] = None,
) -> List[PluginInstallation]:
    q = select(PluginInstallation).order_by(PluginInstallation.connector_code, PluginInstallation.tenant_key)
    if tenant_key:
        q = q.where(PluginInstallation.tenant_key == tenant_key)
    if status:
        q = q.where(PluginInstallation.status == status)
    result = await db.execute(q)
    return list(result.scalars().all())


async def record_plugin_event(
    db: AsyncSession,
    *,
    installation: Optional[PluginInstallation],
    connector_code: str,
    tenant_key: str,
    action: PluginLifecycleAction,
    previous_status: Optional[str],
    new_status: Optional[str],
    actor_id: Optional[uuid.UUID],
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> PluginLifecycleEvent:
    event = PluginLifecycleEvent(
        installation_id=installation.id if installation else None,
        connector_code=connector_code,
        tenant_key=tenant_key,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
        actor_id=actor_id,
        message=message,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(event)
    await db.flush()
    return event


async def install_plugin(
    db: AsyncSession,
    *,
    connector_code: str,
    tenant_key: str = "default",
    environment: str = "sandbox",
    config: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
    actor_id: Optional[uuid.UUID] = None,
) -> PluginInstallation:
    from fastapi import HTTPException

    connector = await get_connector(db, connector_code)
    if connector.status in (ConnectorStatus.COMING_SOON, ConnectorStatus.DEPRECATED):
        raise HTTPException(400, "Connector is not installable in its current lifecycle status")

    missing = []
    for dep_code in _loads_list(connector.dependency_codes):
        dep = await get_installation(db, dep_code, tenant_key=tenant_key)
        if not dep or dep.status not in (PluginInstallStatus.INSTALLED, PluginInstallStatus.UPDATE_AVAILABLE):
            missing.append(dep_code)
    if missing:
        raise HTTPException(400, f"Missing required dependency installation(s): {', '.join(missing)}")

    now = datetime.now(timezone.utc)
    installation = await get_installation(db, connector_code, tenant_key=tenant_key)
    previous = installation.status.value if installation else None
    if installation:
        installation.status = PluginInstallStatus.INSTALLED
        installation.installed_version = connector.current_version
        installation.environment = environment
        installation.config_json = _dumps_config(config)
        installation.installed_by_id = actor_id
        installation.installed_at = installation.installed_at or now
        installation.disabled_at = None
        installation.last_updated_at = now
        installation.notes = notes
    else:
        installation = PluginInstallation(
            connector_id=connector.connector_id,
            connector_code=connector.connector_code,
            tenant_key=tenant_key,
            installed_version=connector.current_version,
            status=PluginInstallStatus.INSTALLED,
            environment=environment,
            config_json=_dumps_config(config),
            installed_by_id=actor_id,
            installed_at=now,
            last_updated_at=now,
            notes=notes,
        )
        db.add(installation)
    connector.is_configured = True
    await db.flush()
    await record_plugin_event(
        db,
        installation=installation,
        connector_code=connector_code,
        tenant_key=tenant_key,
        action=PluginLifecycleAction.INSTALL,
        previous_status=previous,
        new_status=PluginInstallStatus.INSTALLED.value,
        actor_id=actor_id,
        message="Marketplace connector installed",
        metadata={"version": connector.current_version},
    )
    await db.refresh(installation)
    return installation


async def transition_plugin(
    db: AsyncSession,
    *,
    connector_code: str,
    action: PluginLifecycleAction,
    tenant_key: str = "default",
    actor_id: Optional[uuid.UUID] = None,
) -> PluginInstallation:
    from fastapi import HTTPException

    installation = await get_installation(db, connector_code, tenant_key=tenant_key)
    if not installation or installation.status == PluginInstallStatus.UNINSTALLED:
        raise HTTPException(404, "Plugin installation not found")

    previous = installation.status.value
    now = datetime.now(timezone.utc)
    if action == PluginLifecycleAction.DISABLE:
        installation.status = PluginInstallStatus.DISABLED
        installation.disabled_at = now
    elif action == PluginLifecycleAction.ENABLE:
        installation.status = PluginInstallStatus.INSTALLED
        installation.disabled_at = None
    elif action == PluginLifecycleAction.UNINSTALL:
        installation.status = PluginInstallStatus.UNINSTALLED
        installation.disabled_at = now
    elif action == PluginLifecycleAction.UPDATE:
        connector = await get_connector(db, connector_code)
        installation.installed_version = connector.current_version
        installation.status = PluginInstallStatus.INSTALLED
    else:
        raise HTTPException(400, "Unsupported lifecycle action")

    installation.last_updated_at = now
    await db.flush()
    await record_plugin_event(
        db,
        installation=installation,
        connector_code=connector_code,
        tenant_key=tenant_key,
        action=action,
        previous_status=previous,
        new_status=installation.status.value,
        actor_id=actor_id,
        message=f"Marketplace connector {action.value}",
    )
    await db.refresh(installation)
    return installation


async def update_plugin_config(
    db: AsyncSession,
    *,
    connector_code: str,
    tenant_key: str = "default",
    environment: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
    actor_id: Optional[uuid.UUID] = None,
) -> PluginInstallation:
    from fastapi import HTTPException

    installation = await get_installation(db, connector_code, tenant_key=tenant_key)
    if not installation or installation.status == PluginInstallStatus.UNINSTALLED:
        raise HTTPException(404, "Plugin installation not found")
    previous = installation.status.value
    if environment is not None:
        installation.environment = environment
    if config is not None:
        installation.config_json = _dumps_config(config)
    if notes is not None:
        installation.notes = notes
    installation.last_updated_at = datetime.now(timezone.utc)
    await db.flush()
    await record_plugin_event(
        db,
        installation=installation,
        connector_code=connector_code,
        tenant_key=tenant_key,
        action=PluginLifecycleAction.CONFIGURE,
        previous_status=previous,
        new_status=installation.status.value,
        actor_id=actor_id,
        message="Marketplace connector configuration updated",
    )
    await db.refresh(installation)
    return installation


async def list_plugin_events(
    db: AsyncSession,
    connector_code: Optional[str] = None,
    tenant_key: Optional[str] = None,
    limit: int = 100,
) -> List[PluginLifecycleEvent]:
    q = select(PluginLifecycleEvent).order_by(desc(PluginLifecycleEvent.created_at)).limit(limit)
    if connector_code:
        q = q.where(PluginLifecycleEvent.connector_code == connector_code)
    if tenant_key:
        q = q.where(PluginLifecycleEvent.tenant_key == tenant_key)
    result = await db.execute(q)
    return list(result.scalars().all())
