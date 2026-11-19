"""Sign-in for people outside the company: distributors/customers (realm "portal") and suppliers (realm "supplier").

Each realm has its own signed JWT in its own HttpOnly cookie. Tokens carry a ``realm`` claim, so a staff token is
never accepted here and an external token is never accepted by the staff ``get_current_user``. A token also carries
a fingerprint of the password hash, so changing a password (or a hash upgrade) ends earlier sessions. Passwords are
bcrypt; legacy unsalted SHA-256 hashes still verify once and are upgraded to bcrypt on that login.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import token_blocklist
from app.core.config import settings
from app.core.login_limiter import check_login_allowed, clear_login_failures, record_login_failure
from app.core.security import ALGORITHM, hash_password, verify_password
from app.db.session import get_db

COOKIES = {"portal": "erp_portal_token", "supplier": "erp_supplier_token"}
TOKEN_HOURS = 12
_LEGACY_SHA256 = re.compile(r"[0-9a-f]{64}")


def check_password(plain: str, stored: str | None) -> tuple[bool, bool]:
    """(matches, needs_upgrade). Legacy SHA-256 hashes match in constant time and must be re-hashed."""
    if not stored:
        return False, False
    if _LEGACY_SHA256.fullmatch(stored):
        return hmac.compare_digest(hashlib.sha256(plain.encode()).hexdigest(), stored), True
    try:
        return verify_password(plain, stored), False
    except (ValueError, TypeError):
        return False, False


def _fingerprint(password_hash: str | None) -> str:
    return hashlib.sha256((password_hash or "").encode()).hexdigest()[:16]


def issue(response: Response, realm: str, user_id, password_hash: str | None) -> None:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    token = jwt.encode({"sub": str(user_id), "realm": realm, "pwf": _fingerprint(password_hash), "exp": exp,
                        "jti": str(uuid.uuid4())}, settings.SECRET_KEY, algorithm=ALGORITHM)
    response.set_cookie(COOKIES[realm], token, max_age=TOKEN_HOURS * 3600, httponly=True,
                        secure=settings.AUTH_COOKIE_SECURE, samesite=settings.AUTH_COOKIE_SAMESITE, path="/")


async def sign_out(request: Request, response: Response, realm: str) -> None:
    token = request.cookies.get(COOKIES[realm])
    if token:
        try:
            exp = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])["exp"]
            await token_blocklist.add(token, float(exp))
        except jwt.PyJWTError:
            pass
    response.delete_cookie(COOKIES[realm], httponly=True, secure=settings.AUTH_COOKIE_SECURE,
                           samesite=settings.AUTH_COOKIE_SAMESITE, path="/")


async def login_guard(realm: str, email: str):
    key = f"{realm}:{email.strip().lower()}"
    await check_login_allowed(key)
    return key


async def _claims(request: Request, realm: str) -> dict:
    token = request.cookies.get(COOKIES[realm])
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    if not token or await token_blocklist.is_blocked(token):
        raise unauthorized
    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise unauthorized
    if claims.get("realm") != realm:
        raise unauthorized
    try:
        claims["uid"] = uuid.UUID(str(claims.get("sub")))
    except ValueError:
        raise unauthorized
    return claims


async def get_portal_user(request: Request, db: AsyncSession = Depends(get_db)):
    """The signed-in distributor/customer portal user, with an ACTIVE account."""
    from app.models.portal import PortalAccountStatus, PortalUser

    claims = await _claims(request, "portal")
    user = (await db.execute(select(PortalUser).options(selectinload(PortalUser.account))
                             .where(PortalUser.id == claims["uid"]))).scalar_one_or_none()
    if (user is None or not user.is_active or user.account.portal_status != PortalAccountStatus.ACTIVE
            or not hmac.compare_digest(claims.get("pwf", ""), _fingerprint(user.password_hash))):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    return user


async def get_supplier_user(request: Request, db: AsyncSession = Depends(get_db)):
    """The signed-in supplier portal user, with an ACTIVE account."""
    from app.models.supplier_portal import SPAccount, SPAccountStatus, SPUser

    claims = await _claims(request, "supplier")
    user = (await db.execute(select(SPUser).where(SPUser.id == claims["uid"]))).scalar_one_or_none()
    account = await db.get(SPAccount, user.account_id) if user else None
    if (user is None or not user.is_active or account is None or account.portal_status != SPAccountStatus.ACTIVE
            or not hmac.compare_digest(claims.get("pwf", ""), _fingerprint(user.password_hash))):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in.")
    user.account = account
    return user


async def password_login(db: AsyncSession, response: Response, realm: str, user, password: str, key: str) -> bool:
    """Shared password check: rate-limited, upgrades legacy hashes, issues the realm cookie."""
    ok, upgrade = check_password(password, getattr(user, "password_hash", None))
    if not ok:
        await record_login_failure(key)
        return False
    if upgrade:
        user.password_hash = hash_password(password)
    clear_login_failures(key)
    issue(response, realm, user.id, user.password_hash)
    return True
