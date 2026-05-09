"""API Developer Portal endpoints.

Prefix: /api/v1/developer
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.api_portal import ApiKey, ApiKeyUsageLog
from app.models.user import User

router = APIRouter()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, prefix, key_hash)."""
    raw = "erp_" + secrets.token_urlsafe(40)
    prefix = raw[:12]
    return raw, prefix, _hash_key(raw)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    key_name: str
    scopes: Optional[str] = "read"
    rate_limit_per_min: int = 60
    description: Optional[str] = None
    expires_at: Optional[datetime] = None


class ApiKeyOut(BaseModel):
    key_id: str
    key_name: str
    key_prefix: str
    scopes: Optional[str]
    rate_limit_per_min: int
    is_active: bool
    created_at: str
    last_used_at: Optional[str]
    expires_at: Optional[str]
    description: Optional[str]

    @classmethod
    def from_orm(cls, k: ApiKey) -> "ApiKeyOut":
        return cls(
            key_id=str(k.key_id),
            key_name=k.key_name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            rate_limit_per_min=k.rate_limit_per_min,
            is_active=k.is_active,
            created_at=k.created_at.isoformat() if k.created_at else "",
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            expires_at=k.expires_at.isoformat() if k.expires_at else None,
            description=k.description,
        )


# ── API Key CRUD ──────────────────────────────────────────────────────────────

@router.post("/keys", status_code=201)
async def create_api_key(
    payload: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a new API key. Raw key shown ONCE — store it safely."""
    raw, prefix, key_hash = _generate_api_key()

    key = ApiKey(
        user_id=str(current_user.id),
        key_name=payload.key_name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=payload.scopes,
        rate_limit_per_min=payload.rate_limit_per_min,
        description=payload.description,
        expires_at=payload.expires_at,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)

    return {
        **ApiKeyOut.from_orm(key).model_dump(),
        "raw_key": raw,
        "warning": "Store this key securely — it will NOT be shown again.",
    }


@router.get("/keys", response_model=List[ApiKeyOut])
async def list_api_keys(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all API keys for the current user."""
    q = select(ApiKey).where(ApiKey.user_id == str(current_user.id))
    if not include_inactive:
        q = q.where(ApiKey.is_active == True)
    q = q.order_by(desc(ApiKey.created_at))
    r = await db.execute(q)
    return [ApiKeyOut.from_orm(k) for k in r.scalars().all()]


@router.delete("/keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke (deactivate) an API key."""
    r = await db.execute(
        select(ApiKey).where(
            ApiKey.key_id == uuid.UUID(key_id),
            ApiKey.user_id == str(current_user.id),
        )
    )
    key = r.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    await db.commit()


# ── Usage Logs ────────────────────────────────────────────────────────────────

@router.get("/keys/{key_id}/usage")
async def key_usage(
    key_id: str,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent usage logs for an API key."""
    r = await db.execute(
        select(ApiKey).where(
            ApiKey.key_id == uuid.UUID(key_id),
            ApiKey.user_id == str(current_user.id),
        )
    )
    key = r.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    logs_r = await db.execute(
        select(ApiKeyUsageLog)
        .where(ApiKeyUsageLog.key_id == uuid.UUID(key_id))
        .order_by(desc(ApiKeyUsageLog.created_at))
        .limit(limit)
    )
    logs = logs_r.scalars().all()
    return [
        {
            "log_id": str(lg.log_id),
            "endpoint": lg.endpoint,
            "method": lg.method,
            "status_code": lg.status_code,
            "response_ms": lg.response_ms,
            "created_at": lg.created_at.isoformat() if lg.created_at else "",
        }
        for lg in logs
    ]


# ── Developer Dashboard ───────────────────────────────────────────────────────

@router.get("/dashboard")
async def developer_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Aggregated stats for the developer portal dashboard."""
    user_id = str(current_user.id)

    r_total = await db.execute(
        select(func.count()).select_from(ApiKey).where(ApiKey.user_id == user_id)
    )
    total_keys = r_total.scalar() or 0

    r_active = await db.execute(
        select(func.count()).select_from(ApiKey).where(
            ApiKey.user_id == user_id, ApiKey.is_active == True
        )
    )
    active_keys = r_active.scalar() or 0

    # Recent usage across all user keys
    user_key_ids_r = await db.execute(
        select(ApiKey.key_id).where(ApiKey.user_id == user_id)
    )
    key_ids = [row[0] for row in user_key_ids_r.all()]

    total_calls = 0
    success_calls = 0
    error_calls = 0
    if key_ids:
        r_calls = await db.execute(
            select(func.count()).select_from(ApiKeyUsageLog).where(
                ApiKeyUsageLog.key_id.in_(key_ids)
            )
        )
        total_calls = r_calls.scalar() or 0

        r_success = await db.execute(
            select(func.count()).select_from(ApiKeyUsageLog).where(
                ApiKeyUsageLog.key_id.in_(key_ids),
                ApiKeyUsageLog.status_code < 400,
            )
        )
        success_calls = r_success.scalar() or 0
        error_calls = total_calls - success_calls

    return {
        "total_keys": total_keys,
        "active_keys": active_keys,
        "total_api_calls": total_calls,
        "success_calls": success_calls,
        "error_calls": error_calls,
        "available_scopes": ["read", "write", "admin"],
        "default_rate_limit": 60,
    }


# ── GraphQL Stub ──────────────────────────────────────────────────────────────

@router.get("/graphql/schema")
async def graphql_schema_info(_=Depends(get_current_user)):
    """GraphQL layer information — stub. Integrate strawberry-graphql for production."""
    return {
        "status": "stub",
        "note": (
            "GraphQL endpoint not yet wired. "
            "To enable: install strawberry-graphql[fastapi], define schema, "
            "and mount router at /graphql. "
            "All REST endpoints remain the primary API."
        ),
        "planned_types": [
            "Product", "Material", "SalesOrder", "PurchaseOrder",
            "Inventory", "Customer", "Supplier", "ProductionOrder",
        ],
        "planned_queries": [
            "products(filter, limit, offset)",
            "salesOrders(status, customer_id, date_from, date_to)",
            "inventoryLevels(warehouse_id, sku)",
            "customer(id)",
        ],
        "planned_mutations": [
            "createSalesOrder(input)",
            "approveRequest(requestId, comment)",
        ],
        "rest_api_base": "/api/v1",
    }


# ── SDK / Postman info ────────────────────────────────────────────────────────

@router.get("/resources")
async def developer_resources(_=Depends(get_current_user)):
    """Developer resources: SDK links, Postman collection info, docs."""
    return {
        "openapi_json": "/api/v1/openapi.json",
        "openapi_ui": "/docs",
        "redoc_ui": "/redoc",
        "postman_collection_note": (
            "Export from /api/v1/openapi.json using Postman's OpenAPI import. "
            "Set {{base_url}} to your deployment URL."
        ),
        "authentication": {
            "method": "Bearer token (JWT)",
            "header": "Authorization: Bearer <token>",
            "obtain_token": "POST /api/v1/auth/login",
            "api_key_note": "API key auth middleware integration planned — set X-API-Key header.",
        },
        "rate_limits": {
            "default": "60 req/min per key",
            "burst": "100 req/min short burst",
        },
        "sdk_note": "JavaScript and Python SDKs planned. Currently use native HTTP or the OpenAPI spec.",
        "webhooks": {
            "docs": "/api/v1/webhooks/event-definitions",
            "subscriptions": "/api/v1/webhooks/subscriptions",
        },
    }
