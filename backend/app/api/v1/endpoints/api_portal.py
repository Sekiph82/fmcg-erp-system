"""API Developer Portal endpoints.

Prefix: /api/v1/developer
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.deps import get_current_user, get_db, require_permission
from app.models.api_portal import ApiClientApplication, ApiKey, ApiKeyUsageLog, ApiOAuthClientSecret
from app.models.user import User

router = APIRouter()

API_KEY_SCOPE_ORDER = ("read", "write", "admin")
API_KEY_DEFAULT_RATE_LIMIT_PER_MIN = 60
API_KEY_MIN_RATE_LIMIT_PER_MIN = 1
API_KEY_MAX_RATE_LIMIT_PER_MIN = 1000

# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, prefix, key_hash)."""
    raw = "erp_" + secrets.token_urlsafe(40)
    prefix = raw[:12]
    return raw, prefix, _hash_key(raw)


def _generate_oauth_client_secret() -> tuple[str, str, str]:
    """Returns (raw_secret, display_prefix, SHA-256 hash) for a high-entropy secret."""
    raw = "erp_oauth_" + secrets.token_urlsafe(48)
    return raw, raw[:16], _hash_key(raw)


def _validated_expiry(value: Optional[datetime], *, legacy_timestamp: bool = False) -> Optional[datetime]:
    if value is None:
        return None
    normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    if normalized <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Credential expiry must be in the future.")
    return normalized.replace(tzinfo=None) if legacy_timestamp else normalized


def _serialize_legacy_utc(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return normalized.isoformat()


def _canonicalize_scopes(value: str) -> str:
    parts = [item.strip().lower() for item in value.split(",")]
    if not parts or any(not item for item in parts):
        raise ValueError("Scopes must be a comma-separated list of read, write, or admin.")
    if len(parts) != len(set(parts)):
        raise ValueError("Scopes must not contain duplicates.")
    unknown = sorted(set(parts) - set(API_KEY_SCOPE_ORDER))
    if unknown:
        raise ValueError(f"Unsupported API key scope: {', '.join(unknown)}.")
    if "admin" in parts:
        if len(parts) != 1:
            raise ValueError("The admin API key scope must be used alone.")
        return "admin"
    return ",".join(scope for scope in API_KEY_SCOPE_ORDER if scope in parts)


async def _owned_active_application(
    db: AsyncSession, application_id: uuid.UUID, owner_id: uuid.UUID
) -> ApiClientApplication:
    result = await db.execute(
        select(ApiClientApplication).where(
            ApiClientApplication.client_id == application_id,
            ApiClientApplication.owner_user_id == owner_id,
        ).with_for_update()
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=404, detail="API client application not found.")
    if not application.is_active:
        raise HTTPException(status_code=409, detail="Credentials cannot be issued for an inactive application.")
    return application


# ── Schemas ───────────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    application_id: uuid.UUID
    key_name: str = Field(min_length=1, max_length=200)
    scopes: Optional[str] = Field(default="read", max_length=32)
    rate_limit_per_min: int = Field(
        default=API_KEY_DEFAULT_RATE_LIMIT_PER_MIN,
        ge=API_KEY_MIN_RATE_LIMIT_PER_MIN,
        le=API_KEY_MAX_RATE_LIMIT_PER_MIN,
    )
    description: Optional[str] = None
    expires_at: Optional[datetime] = None

    @field_validator("key_name")
    @classmethod
    def trim_key_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Key name must not be blank")
        return value

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: Optional[str]) -> str:
        return "read" if value is None else _canonicalize_scopes(value)


class ApiKeyRotate(BaseModel):
    expires_at: Optional[datetime] = None
    scopes: Optional[str] = None
    rate_limit_per_min: Optional[int] = Field(
        default=None,
        ge=API_KEY_MIN_RATE_LIMIT_PER_MIN,
        le=API_KEY_MAX_RATE_LIMIT_PER_MIN,
    )

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: Optional[str]) -> Optional[str]:
        return _canonicalize_scopes(value) if value is not None else None


class ApiOAuthClientSecretCreate(BaseModel):
    secret_name: str = Field(min_length=1, max_length=160)
    expires_at: Optional[datetime] = None

    @field_validator("secret_name")
    @classmethod
    def trim_secret_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Secret name must not be blank")
        return value


class ApiKeyOut(BaseModel):
    key_id: str
    application_id: Optional[str]
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
            application_id=str(k.application_id) if k.application_id else None,
            key_name=k.key_name,
            key_prefix=k.key_prefix,
            scopes=k.scopes,
            rate_limit_per_min=k.rate_limit_per_min,
            is_active=k.is_active,
            created_at=k.created_at.isoformat() if k.created_at else "",
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
            # dev_api_keys.expires_at predates timezone-aware storage and is
            # interpreted as UTC by the lifecycle API. Always include the UTC
            # offset so browser clients do not parse it as local wall time.
            expires_at=_serialize_legacy_utc(k.expires_at),
            description=k.description,
        )


class ApiOAuthClientSecretOut(BaseModel):
    secret_id: str
    application_id: str
    secret_name: str
    secret_prefix: str
    is_active: bool
    created_at: str
    expires_at: Optional[str]

    @classmethod
    def from_orm(cls, credential: ApiOAuthClientSecret) -> "ApiOAuthClientSecretOut":
        return cls(
            secret_id=str(credential.secret_id),
            application_id=str(credential.application_id),
            secret_name=credential.secret_name,
            secret_prefix=credential.secret_prefix,
            is_active=credential.is_active,
            created_at=credential.created_at.isoformat() if credential.created_at else "",
            expires_at=credential.expires_at.isoformat() if credential.expires_at else None,
        )


ApplicationEnvironment = Literal["development", "sandbox", "production"]


class ApiClientApplicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=2000)
    environment: ApplicationEnvironment = "development"

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Application name must not be blank")
        return value


class ApiClientApplicationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=2000)
    environment: Optional[ApplicationEnvironment] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Application name must not be blank")
        return value


class ApiClientApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: uuid.UUID
    name: str
    description: Optional[str]
    environment: ApplicationEnvironment
    is_active: bool
    created_at: datetime
    updated_at: datetime


@router.get(
    "/applications",
    response_model=List[ApiClientApplicationOut],
    dependencies=[Depends(require_permission("integrations", "view"))],
)
async def list_client_applications(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List API client applications owned by the authenticated user."""
    query = select(ApiClientApplication).where(
        ApiClientApplication.owner_user_id == current_user.id
    )
    if not include_inactive:
        query = query.where(ApiClientApplication.is_active.is_(True))
    query = query.order_by(desc(ApiClientApplication.created_at), ApiClientApplication.client_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/applications",
    status_code=201,
    response_model=ApiClientApplicationOut,
    dependencies=[Depends(require_permission("integrations", "edit"))],
)
async def create_client_application(
    payload: ApiClientApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register application metadata without creating or exposing credentials."""
    application = ApiClientApplication(
        owner_user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        environment=payload.environment,
    )
    db.add(application)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An application with this name and environment is already registered.",
        ) from exc
    await db.refresh(application)
    return application


@router.patch(
    "/applications/{client_id}",
    response_model=ApiClientApplicationOut,
    dependencies=[Depends(require_permission("integrations", "edit"))],
)
async def update_client_application(
    client_id: uuid.UUID,
    payload: ApiClientApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update owned application metadata or deactivate/reactivate its registry record."""
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one application field must be provided.")
    if any(changes.get(field) is None for field in ("name", "environment", "is_active") if field in changes):
        raise HTTPException(status_code=422, detail="Name, environment, and active status cannot be null.")

    result = await db.execute(
        select(ApiClientApplication).where(
            ApiClientApplication.client_id == client_id,
            ApiClientApplication.owner_user_id == current_user.id,
        ).with_for_update()
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(status_code=404, detail="API client application not found.")
    for field, value in changes.items():
        setattr(application, field, value)
    if changes.get("is_active") is False:
        # Disabling an application is a credential kill switch. Re-enabling it
        # does not silently restore credentials that were revoked here.
        keys_result = await db.execute(
            select(ApiKey).where(ApiKey.application_id == application.client_id, ApiKey.is_active.is_(True))
        )
        for key in keys_result.scalars().all():
            key.is_active = False
        secrets_result = await db.execute(
            select(ApiOAuthClientSecret).where(
                ApiOAuthClientSecret.application_id == application.client_id,
                ApiOAuthClientSecret.is_active.is_(True),
            )
        )
        for credential in secrets_result.scalars().all():
            credential.is_active = False
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An application with this name and environment is already registered.",
        ) from exc
    await db.refresh(application)
    return application


# ── API Key CRUD ──────────────────────────────────────────────────────────────

@router.post(
    "/keys",
    status_code=201,
    dependencies=[Depends(require_permission("integrations", "edit"))],
)
async def create_api_key(
    payload: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue an application-owned API key. The raw value is returned once and never persisted."""
    await _owned_active_application(db, payload.application_id, current_user.id)
    if "admin" in (payload.scopes or "read").split(",") and not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="The admin API-key scope can only be issued by a superuser.")
    raw, prefix, key_hash = _generate_api_key()

    key = ApiKey(
        user_id=str(current_user.id),
        application_id=payload.application_id,
        key_name=payload.key_name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=payload.scopes or "read",
        rate_limit_per_min=payload.rate_limit_per_min,
        description=payload.description,
        expires_at=_validated_expiry(payload.expires_at, legacy_timestamp=True),
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)

    return {
        **ApiKeyOut.from_orm(key).model_dump(),
        "raw_key": raw,
        "warning": "Store this key securely — it will NOT be shown again.",
    }


@router.get(
    "/keys",
    response_model=List[ApiKeyOut],
    dependencies=[Depends(require_permission("integrations", "view"))],
)
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


@router.delete(
    "/keys/{key_id}",
    status_code=204,
    dependencies=[Depends(require_permission("integrations", "edit"))],
)
async def revoke_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke (deactivate) an API key."""
    r = await db.execute(
        select(ApiKey).where(
            ApiKey.key_id == key_id,
            ApiKey.user_id == str(current_user.id),
        )
    )
    key = r.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    await db.commit()


@router.post(
    "/keys/{key_id}/rotate",
    status_code=201,
    dependencies=[Depends(require_permission("integrations", "edit"))],
)
async def rotate_api_key(
    key_id: uuid.UUID,
    payload: ApiKeyRotate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace an owned API key atomically; show the new raw value once."""
    initial_result = await db.execute(
        select(ApiKey).where(ApiKey.key_id == key_id, ApiKey.user_id == str(current_user.id))
    )
    initial = initial_result.scalar_one_or_none()
    if initial is None:
        raise HTTPException(status_code=404, detail="API key not found.")
    if initial.application_id is not None:
        await _owned_active_application(db, initial.application_id, current_user.id)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_id == key_id, ApiKey.user_id == str(current_user.id)).with_for_update()
    )
    previous = result.scalar_one_or_none()
    if previous is None:
        raise HTTPException(status_code=404, detail="API key not found.")
    if previous.application_id != initial.application_id:
        raise HTTPException(status_code=409, detail="API key application changed; reload and retry.")
    if not previous.is_active:
        raise HTTPException(status_code=409, detail="An inactive API key cannot be rotated.")

    expiry = (
        _validated_expiry(payload.expires_at, legacy_timestamp=True)
        if "expires_at" in payload.model_fields_set
        else _validated_expiry(previous.expires_at, legacy_timestamp=True)
    )
    if "scopes" in payload.model_fields_set and payload.scopes is None:
        raise HTTPException(status_code=422, detail="Scopes cannot be null when changed.")
    scopes = payload.scopes if "scopes" in payload.model_fields_set else (previous.scopes or "read")
    try:
        scopes = _canonicalize_scopes(scopes)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="This legacy API key has unsupported scopes; choose new scopes when rotating.") from exc
    if "admin" in scopes.split(",") and not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="The admin API-key scope can only be issued by a superuser.")
    if "rate_limit_per_min" in payload.model_fields_set and payload.rate_limit_per_min is None:
        raise HTTPException(status_code=422, detail="Rate limit cannot be null when changed.")
    rate_limit = payload.rate_limit_per_min if "rate_limit_per_min" in payload.model_fields_set else previous.rate_limit_per_min
    if not API_KEY_MIN_RATE_LIMIT_PER_MIN <= rate_limit <= API_KEY_MAX_RATE_LIMIT_PER_MIN:
        raise HTTPException(
            status_code=409,
            detail=f"This legacy API key's rate limit is outside the current {API_KEY_MIN_RATE_LIMIT_PER_MIN}-{API_KEY_MAX_RATE_LIMIT_PER_MIN} range; choose a new rate when rotating.",
        )
    raw, prefix, key_hash = _generate_api_key()
    replacement = ApiKey(
        user_id=previous.user_id,
        application_id=previous.application_id,
        key_name=previous.key_name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=scopes,
        rate_limit_per_min=rate_limit,
        description=previous.description,
        expires_at=expiry,
    )
    previous.is_active = False
    db.add(replacement)
    await db.commit()
    await db.refresh(replacement)
    return {
        **ApiKeyOut.from_orm(replacement).model_dump(),
        "replaces_key_id": str(previous.key_id),
        "raw_key": raw,
        "warning": "The previous key was revoked. Store this replacement securely; it will not be shown again.",
    }


@router.get(
    "/applications/{application_id}/oauth-secrets",
    response_model=List[ApiOAuthClientSecretOut],
    dependencies=[Depends(require_permission("integrations", "view"))],
)
async def list_oauth_client_secrets(
    application_id: uuid.UUID,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List secret metadata for an owned application; secret values are never returned."""
    app_result = await db.execute(
        select(ApiClientApplication.client_id).where(
            ApiClientApplication.client_id == application_id,
            ApiClientApplication.owner_user_id == current_user.id,
        )
    )
    if app_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="API client application not found.")
    query = select(ApiOAuthClientSecret).where(ApiOAuthClientSecret.application_id == application_id)
    if not include_inactive:
        query = query.where(ApiOAuthClientSecret.is_active.is_(True))
    result = await db.execute(query.order_by(desc(ApiOAuthClientSecret.created_at), ApiOAuthClientSecret.secret_id))
    return [ApiOAuthClientSecretOut.from_orm(item) for item in result.scalars().all()]


@router.post(
    "/applications/{application_id}/oauth-secrets",
    status_code=201,
    dependencies=[Depends(require_permission("integrations", "edit"))],
)
async def create_oauth_client_secret(
    application_id: uuid.UUID,
    payload: ApiOAuthClientSecretCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue an OAuth client-secret credential record; this does not enable OAuth token issuance."""
    await _owned_active_application(db, application_id, current_user.id)
    raw, prefix, secret_hash = _generate_oauth_client_secret()
    credential = ApiOAuthClientSecret(
        application_id=application_id,
        secret_name=payload.secret_name,
        secret_prefix=prefix,
        secret_hash=secret_hash,
        expires_at=_validated_expiry(payload.expires_at),
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return {
        **ApiOAuthClientSecretOut.from_orm(credential).model_dump(),
        "client_id": str(application_id),
        "client_secret": raw,
        "warning": "Store this secret securely. It will not be shown again. OAuth token issuance is not enabled by this credential registry.",
    }


@router.post(
    "/applications/{application_id}/oauth-secrets/{secret_id}/rotate",
    status_code=201,
    dependencies=[Depends(require_permission("integrations", "edit"))],
)
async def rotate_oauth_client_secret(
    application_id: uuid.UUID,
    secret_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace an owned OAuth client secret atomically and show the replacement once."""
    await _owned_active_application(db, application_id, current_user.id)
    result = await db.execute(
        select(ApiOAuthClientSecret).where(
            ApiOAuthClientSecret.secret_id == secret_id,
            ApiOAuthClientSecret.application_id == application_id,
        ).with_for_update()
    )
    previous = result.scalar_one_or_none()
    if previous is None:
        raise HTTPException(status_code=404, detail="OAuth client secret not found.")
    if not previous.is_active:
        raise HTTPException(status_code=409, detail="An inactive secret cannot be rotated.")
    raw, prefix, secret_hash = _generate_oauth_client_secret()
    expiry = _validated_expiry(previous.expires_at)
    replacement = ApiOAuthClientSecret(
        application_id=application_id,
        secret_name=previous.secret_name,
        secret_prefix=prefix,
        secret_hash=secret_hash,
        expires_at=expiry,
    )
    previous.is_active = False
    db.add(replacement)
    await db.commit()
    await db.refresh(replacement)
    return {
        **ApiOAuthClientSecretOut.from_orm(replacement).model_dump(),
        "client_id": str(application_id),
        "replaces_secret_id": str(previous.secret_id),
        "client_secret": raw,
        "warning": "The previous secret was revoked. Store this replacement securely; OAuth token issuance is not enabled by this credential registry.",
    }


@router.delete(
    "/applications/{application_id}/oauth-secrets/{secret_id}",
    status_code=204,
    dependencies=[Depends(require_permission("integrations", "edit"))],
)
async def revoke_oauth_client_secret(
    application_id: uuid.UUID,
    secret_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke an OAuth client secret belonging to an owned application."""
    result = await db.execute(
        select(ApiOAuthClientSecret)
        .join(ApiClientApplication, ApiClientApplication.client_id == ApiOAuthClientSecret.application_id)
        .where(
            ApiOAuthClientSecret.secret_id == secret_id,
            ApiOAuthClientSecret.application_id == application_id,
            ApiClientApplication.owner_user_id == current_user.id,
        )
    )
    credential = result.scalar_one_or_none()
    if credential is None:
        raise HTTPException(status_code=404, detail="OAuth client secret not found.")
    credential.is_active = False
    await db.commit()


# ── Usage Logs ────────────────────────────────────────────────────────────────

@router.get(
    "/keys/{key_id}/usage",
    dependencies=[Depends(require_permission("integrations", "view"))],
)
async def key_usage(
    key_id: uuid.UUID,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent usage logs for an API key."""
    r = await db.execute(
        select(ApiKey).where(
            ApiKey.key_id == key_id,
            ApiKey.user_id == str(current_user.id),
        )
    )
    key = r.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    logs_r = await db.execute(
        select(ApiKeyUsageLog)
        .where(ApiKeyUsageLog.key_id == key_id)
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
        "available_scopes": list(API_KEY_SCOPE_ORDER),
        "default_rate_limit": API_KEY_DEFAULT_RATE_LIMIT_PER_MIN,
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
            "method": "HttpOnly session cookie (JWT)",
            "header": f"Cookie: {settings.AUTH_COOKIE_NAME}=<session>",
            "obtain_token": "Sign in through the ERP login flow; the browser receives the HttpOnly session cookie.",
            "api_key_note": "API-key request authentication is not enabled; the developer portal currently manages credential metadata only.",
        },
        "rate_limits": {
            "default": f"{API_KEY_DEFAULT_RATE_LIMIT_PER_MIN} requests per minute per key",
            "minimum": API_KEY_MIN_RATE_LIMIT_PER_MIN,
            "maximum": API_KEY_MAX_RATE_LIMIT_PER_MIN,
            "window": "60 seconds",
            "enforcement": "Stored configuration only; not enforced until API-key request authentication is enabled.",
        },
        "api_key_scopes": {
            "read": "Future key-authenticated GET/HEAD read ceiling; not currently enforced.",
            "write": "Future key-authenticated read plus POST/PUT/PATCH/DELETE ceiling; not currently enforced.",
            "admin": "Future full-access ceiling, issued by a superuser and used alone; not currently enforced.",
        },
        "sdk_note": "JavaScript and Python SDKs planned. Currently use native HTTP or the OpenAPI spec.",
        "webhooks": {
            "docs": "/api/v1/webhooks/event-definitions",
            "subscriptions": "/api/v1/webhooks/subscriptions",
        },
    }
