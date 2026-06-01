import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

# passlib 1.7.x internally calls bcrypt.hashpw with a 73-byte probe string.
# bcrypt 4.1+ raises ValueError for passwords over 72 bytes (changed from silent
# truncation). Patch only when the installed bcrypt actually raises, so this is
# a no-op on bcrypt <4.1 and auto-repairs on 4.1+/5.x without hard-coding versions.
try:
    import bcrypt as _bcrypt_module
    if not getattr(_bcrypt_module.hashpw, '_compat_patched', False):
        _needs_compat = False
        try:
            _bcrypt_module.hashpw(b'A' * 73, _bcrypt_module.gensalt())
        except (ValueError, TypeError):
            _needs_compat = True
        if _needs_compat:
            _orig_hashpw = _bcrypt_module.hashpw
            def _hashpw_compat(password, *args, **kwargs):
                if isinstance(password, (bytes, bytearray)) and len(password) > 72:
                    password = password[:72]
                return _orig_hashpw(password, *args, **kwargs)
            _hashpw_compat._compat_patched = True
            _bcrypt_module.hashpw = _hashpw_compat
except Exception:
    pass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: Any, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode({"sub": str(subject), "exp": expire, "jti": str(uuid.uuid4())}, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError as e:
        logger.debug("Token decode failed: %s", e)
        return None
