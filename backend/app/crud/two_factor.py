"""CRUD helpers for 2FA models."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.two_factor import (
    User2FASettings, TwoFASession, RecoveryCode,
    TwoFAMethod, TwoFASessionStatus,
)
from app.core.totp import (
    hash_recovery_code, verify_recovery_code, otp_expires_at,
)

MAX_ATTEMPTS = 5


# ── User2FASettings ────────────────────────────────────────────────────────────

async def get_2fa_settings(db: AsyncSession, user_id: uuid.UUID) -> Optional[User2FASettings]:
    result = await db.execute(
        select(User2FASettings).where(User2FASettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_2fa_settings(
    db: AsyncSession, user_id: uuid.UUID, method: TwoFAMethod = TwoFAMethod.TOTP
) -> User2FASettings:
    settings = await get_2fa_settings(db, user_id)
    if not settings:
        settings = User2FASettings(user_id=user_id, method=method)
        db.add(settings)
        await db.flush()
    return settings


# ── TwoFASession ───────────────────────────────────────────────────────────────

async def create_2fa_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    settings_id: uuid.UUID,
    method: TwoFAMethod,
    challenge_code: Optional[str] = None,
) -> TwoFASession:
    session = TwoFASession(
        user_id=user_id,
        settings_id=settings_id,
        method=method,
        challenge_code=challenge_code,
        expires_at=otp_expires_at(),
        status=TwoFASessionStatus.PENDING,
        attempt_count="0",
    )
    db.add(session)
    await db.flush()
    return session


async def get_2fa_session(db: AsyncSession, session_id: uuid.UUID) -> Optional[TwoFASession]:
    result = await db.execute(
        select(TwoFASession).where(TwoFASession.id == session_id)
    )
    return result.scalar_one_or_none()


async def mark_session_verified(db: AsyncSession, session: TwoFASession) -> None:
    session.status = TwoFASessionStatus.VERIFIED
    await db.flush()


async def mark_session_failed(db: AsyncSession, session: TwoFASession) -> TwoFASession:
    attempts = int(session.attempt_count) + 1
    session.attempt_count = str(attempts)
    if attempts >= MAX_ATTEMPTS:
        session.status = TwoFASessionStatus.FAILED
    await db.flush()
    return session


async def expire_old_sessions(db: AsyncSession, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(TwoFASession).where(
            and_(
                TwoFASession.user_id == user_id,
                TwoFASession.status == TwoFASessionStatus.PENDING,
            )
        )
    )
    for s in result.scalars().all():
        s.status = TwoFASessionStatus.EXPIRED
    await db.flush()


# ── RecoveryCode ───────────────────────────────────────────────────────────────

async def create_recovery_codes(
    db: AsyncSession, user_id: uuid.UUID, settings_id: uuid.UUID, plaintext_codes: list[str]
) -> None:
    for code in plaintext_codes:
        db.add(RecoveryCode(
            user_id=user_id,
            settings_id=settings_id,
            code_hash=hash_recovery_code(code),
        ))
    await db.flush()


async def delete_recovery_codes(db: AsyncSession, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(RecoveryCode).where(RecoveryCode.user_id == user_id)
    )
    for code in result.scalars().all():
        await db.delete(code)
    await db.flush()


async def get_unused_recovery_codes(db: AsyncSession, user_id: uuid.UUID) -> list[RecoveryCode]:
    result = await db.execute(
        select(RecoveryCode).where(
            and_(RecoveryCode.user_id == user_id, RecoveryCode.used == False)  # noqa: E712
        )
    )
    return list(result.scalars().all())


async def use_recovery_code(
    db: AsyncSession, user_id: uuid.UUID, plain_code: str
) -> bool:
    codes = await get_unused_recovery_codes(db, user_id)
    for code in codes:
        if verify_recovery_code(plain_code, code.code_hash):
            code.used = True
            await db.flush()
            return True
    return False


# ── Reports ────────────────────────────────────────────────────────────────────

async def count_failed_2fa_attempts_last_24h(db: AsyncSession) -> int:
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await db.execute(
        select(func.count()).where(
            and_(
                TwoFASession.status == TwoFASessionStatus.FAILED,
                TwoFASession.created_at >= cutoff,
            )
        )
    )
    return result.scalar_one() or 0


async def get_2fa_method_breakdown(db: AsyncSession) -> dict:
    result = await db.execute(
        select(User2FASettings.method, func.count()).where(
            User2FASettings.is_enabled == True  # noqa: E712
        ).group_by(User2FASettings.method)
    )
    return {row[0]: row[1] for row in result.all()}
