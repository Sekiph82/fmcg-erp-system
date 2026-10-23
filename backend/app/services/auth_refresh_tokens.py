from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.crud import audit as audit_crud
from app.models.audit_log import AuditEvent
from app.models.auth_refresh_token import AuthRefreshToken
from app.models.user import User


class InvalidRefreshToken(Exception):
    """Presented refresh credential is unknown, expired, or revoked."""


class RefreshTokenReuse(InvalidRefreshToken):
    """A consumed refresh token was replayed and its family was revoked."""


@dataclass(frozen=True)
class AuthTokenPair:
    access_token: str
    refresh_token: str
    family_id: uuid.UUID


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def _expiry(now: datetime) -> datetime:
    return now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


async def issue_auth_token_pair(db: AsyncSession, user_id: uuid.UUID | str) -> AuthTokenPair:
    """Create an access JWT and the first hashed refresh credential in a new family."""
    now = datetime.now(timezone.utc)
    family_id = uuid.uuid4()
    refresh_token = _new_refresh_token()
    db.add(AuthRefreshToken(
        family_id=family_id,
        user_id=uuid.UUID(str(user_id)),
        token_hash=_token_hash(refresh_token),
        expires_at=_expiry(now),
    ))
    return AuthTokenPair(
        access_token=create_access_token(str(user_id), session_id=str(family_id)),
        refresh_token=refresh_token,
        family_id=family_id,
    )


async def is_refresh_family_active(db: AsyncSession, family_id: uuid.UUID) -> bool:
    now = datetime.now(timezone.utc)
    return bool(await db.scalar(select(exists().where(
        AuthRefreshToken.family_id == family_id,
        AuthRefreshToken.revoked_at.is_(None),
        AuthRefreshToken.expires_at > now,
    ))))


async def _revoke_family(
    db: AsyncSession,
    family_id: uuid.UUID,
    now: datetime,
    user_id: uuid.UUID | None = None,
) -> int:
    conditions = [
        AuthRefreshToken.family_id == family_id,
        AuthRefreshToken.revoked_at.is_(None),
    ]
    if user_id is not None:
        conditions.append(AuthRefreshToken.user_id == user_id)
    result = await db.execute(
        update(AuthRefreshToken)
        .where(*conditions)
        .values(revoked_at=now)
    )
    return int(result.rowcount or 0)


async def rotate_refresh_token(db: AsyncSession, raw_token: str) -> tuple[AuthTokenPair, User]:
    """Atomically consume one refresh token and issue its sole successor."""
    now = datetime.now(timezone.utc)
    row = await db.scalar(
        select(AuthRefreshToken)
        .where(AuthRefreshToken.token_hash == _token_hash(raw_token))
        .with_for_update()
    )
    if row is None or row.revoked_at is not None:
        raise InvalidRefreshToken

    if row.consumed_at is not None:
        await _revoke_family(db, row.family_id, now)
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.REFRESH_TOKEN_REUSE_DETECTED,
            actor_id=row.user_id,
            target_type="auth_session",
            target_id=str(row.family_id),
            details={"reason": "consumed_refresh_token_replayed"},
        )
        await db.commit()
        raise RefreshTokenReuse

    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        row.revoked_at = now
        await db.commit()
        raise InvalidRefreshToken

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        await _revoke_family(db, row.family_id, now)
        await db.commit()
        raise InvalidRefreshToken

    successor = _new_refresh_token()
    next_row = AuthRefreshToken(
        family_id=row.family_id,
        user_id=row.user_id,
        token_hash=_token_hash(successor),
        # Rotation must not extend the session's absolute lifetime. T002 may
        # add a stricter inactivity policy, but each session keeps the expiry
        # established when the user logged in.
        expires_at=expires_at,
    )
    row.consumed_at = now
    db.add(next_row)
    await db.flush()
    row.replaced_by_id = next_row.id
    await audit_crud.log_event(
        db,
        event_type=AuditEvent.REFRESH_TOKEN_ROTATED,
        actor_id=row.user_id,
        target_type="auth_session",
        target_id=str(row.family_id),
        details={"refresh_token_id": str(row.id), "successor_id": str(next_row.id)},
    )
    return AuthTokenPair(
        access_token=create_access_token(str(user.id), session_id=str(row.family_id)),
        refresh_token=successor,
        family_id=row.family_id,
    ), user


async def revoke_refresh_family(
    db: AsyncSession,
    *,
    family_id: uuid.UUID | None,
    user_id: uuid.UUID,
    now: datetime | None = None,
) -> bool:
    """Revoke all refresh credentials and session-bound access JWTs in a family."""
    if family_id is None:
        return False
    revoked = await _revoke_family(
        db,
        family_id,
        now or datetime.now(timezone.utc),
        user_id=user_id,
    )
    if revoked:
        await audit_crud.log_event(
            db,
            event_type=AuditEvent.REFRESH_TOKEN_REVOKED,
            actor_id=user_id,
            target_type="auth_session",
            target_id=str(family_id),
            details={"reason": "logout"},
        )
    return revoked > 0


async def refresh_family_for_token(
    db: AsyncSession,
    raw_token: str,
    user_id: uuid.UUID,
) -> uuid.UUID | None:
    row = await db.scalar(select(AuthRefreshToken).where(
        AuthRefreshToken.token_hash == _token_hash(raw_token),
        AuthRefreshToken.user_id == user_id,
    ))
    return row.family_id if row is not None else None
