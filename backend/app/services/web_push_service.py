"""Web Push for the installed PWA (M37.S03.T001) — RFC 8291 (aes128gcm) payload encryption and RFC 8292 VAPID,
with the `cryptography` package only.

- The VAPID key pair is created once and kept encrypted in SystemConfig (``web_push.vapid``).
- Each signed-in device subscribes with its browser push endpoint; endpoints answering 404/410 are dropped.
- Every new in-app notification (nc_notifications) is also pushed to the recipient's devices, best effort.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import struct
import time
import uuid
from typing import Iterable, Optional
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)
CONFIG_KEY = "web_push.vapid"
TTL_SECONDS = 24 * 3600
_vapid_cache: Optional[tuple[ec.EllipticCurvePrivateKey, str]] = None


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64u(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _raw_public(key: ec.EllipticCurvePublicKey) -> bytes:
    return key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


def _hkdf(salt: bytes, info: bytes, ikm: bytes, length: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def encrypt(payload: bytes, p256dh: str, auth: str, *, salt: Optional[bytes] = None,
            server_key: Optional[ec.EllipticCurvePrivateKey] = None) -> bytes:
    """aes128gcm body for one subscription (RFC 8291, single record)."""
    ua_public = unb64u(p256dh)
    auth_secret = unb64u(auth)
    if len(ua_public) != 65 or len(auth_secret) < 16:
        raise ValueError("invalid subscription keys")
    as_private = server_key or ec.generate_private_key(ec.SECP256R1())
    as_public = _raw_public(as_private.public_key())
    shared = as_private.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public))
    ikm = _hkdf(auth_secret, b"WebPush: info\x00" + ua_public + as_public, shared, 32)
    salt = salt or os.urandom(16)
    cek = _hkdf(salt, b"Content-Encoding: aes128gcm\x00", ikm, 16)
    nonce = _hkdf(salt, b"Content-Encoding: nonce\x00", ikm, 12)
    if len(payload) > 3800:
        raise ValueError("payload too large")
    body = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    return salt + struct.pack(">I", 4096) + bytes([len(as_public)]) + as_public + body


def vapid_header(endpoint: str, private_key: ec.EllipticCurvePrivateKey, subject: str, now: Optional[int] = None) -> str:
    parts = urlsplit(endpoint)
    claims = {"aud": f"{parts.scheme}://{parts.netloc}", "exp": int(now or time.time()) + 12 * 3600, "sub": subject}
    signing_input = f"{b64u(json.dumps({'typ': 'JWT', 'alg': 'ES256'}, separators=(',', ':')).encode())}." \
                    f"{b64u(json.dumps(claims, separators=(',', ':')).encode())}"
    r, s = decode_dss_signature(private_key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256())))
    jwt = f"{signing_input}.{b64u(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"
    return f"vapid t={jwt}, k={b64u(_raw_public(private_key.public_key()))}"


async def vapid_keys(db: AsyncSession) -> tuple[ec.EllipticCurvePrivateKey, str]:
    """(private key, public key for the browser). Created once, stored encrypted."""
    global _vapid_cache
    if _vapid_cache is not None:
        return _vapid_cache
    from app.models.utilities import ConfigCategory, SystemConfig
    from app.services.provider_credentials import _cipher

    row = (await db.execute(select(SystemConfig).where(SystemConfig.key == CONFIG_KEY))).scalar_one_or_none()
    if row is None:
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        db.add(SystemConfig(key=CONFIG_KEY, value=_cipher().encrypt(pem).decode(), category=ConfigCategory.SYSTEM,
                            description="Web Push VAPID key (encrypted)", is_editable=False))
        try:
            await db.commit()
        except Exception:  # another worker created it first
            await db.rollback()
            row = (await db.execute(select(SystemConfig).where(SystemConfig.key == CONFIG_KEY))).scalar_one()
    if row is not None:
        key = serialization.load_pem_private_key(_cipher().decrypt(row.value.encode()), password=None)
    _vapid_cache = (key, b64u(_raw_public(key.public_key())))
    return _vapid_cache


def _subject() -> str:
    from app.core.config import settings
    url = (settings.PUBLIC_APP_URL or "").rstrip("/")
    return url if url.startswith("https://") else "mailto:noreply@povu.invalid"


async def send_to_users(db: AsyncSession, user_ids: Iterable[str], message: dict, client=None) -> dict:
    """Push `message` ({title, body, url}) to every active subscription of the users. Returns counts."""
    import httpx
    from app.models.mobile import WebPushSubscription

    ids = [uuid.UUID(str(u)) for u in user_ids if u]
    if not ids:
        return {"sent": 0, "failed": 0, "removed": 0}
    subs = (await db.execute(select(WebPushSubscription).where(WebPushSubscription.user_id.in_(ids)))).scalars().all()
    if not subs:
        return {"sent": 0, "failed": 0, "removed": 0}
    key, _ = await vapid_keys(db)
    payload = json.dumps({k: message.get(k) for k in ("title", "body", "url", "tag")}, ensure_ascii=False).encode()[:3500]
    own = client is None
    client = client or httpx.AsyncClient(timeout=10)
    sent = failed = 0
    gone: list = []
    try:
        for sub in subs:
            try:
                resp = await client.post(sub.endpoint, content=encrypt(payload, sub.p256dh, sub.auth), headers={
                    "Authorization": vapid_header(sub.endpoint, key, _subject()), "TTL": str(TTL_SECONDS),
                    "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream", "Urgency": "normal"})
                if resp.status_code in (404, 410):
                    gone.append(sub.id)
                elif resp.status_code < 300:
                    sent += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
                log.warning("web push failed for subscription %s", sub.id, exc_info=True)
    finally:
        if own:
            await client.aclose()
    if gone:
        await db.execute(delete(WebPushSubscription).where(WebPushSubscription.id.in_(gone)))
    if sent:
        await db.execute(update(WebPushSubscription).where(WebPushSubscription.id.in_([s.id for s in subs if s.id not in gone]))
                         .values(last_sent_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)))
    await db.commit()
    return {"sent": sent, "failed": failed, "removed": len(gone)}


# ── every new in-app notification is also pushed (best effort, after commit) ─────

_hook_installed = False


def install_notification_hook() -> None:
    global _hook_installed
    if _hook_installed:
        return
    _hook_installed = True
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    from app.models.notifications import Notification

    @event.listens_for(Session, "after_flush")
    def _collect(session, _ctx):
        new = [n for n in session.new if isinstance(n, Notification) and n.scheduled_for is None]
        if new:
            session.info.setdefault("web_push", []).extend(
                {"user_id": n.user_id, "title": n.title, "body": (n.message or "")[:240],
                 "url": "/dashboard/notification-center", "tag": str(n.notification_id)} for n in new)

    @event.listens_for(Session, "after_commit")
    def _send(session):
        items = session.info.pop("web_push", None)
        if not items:
            return
        try:
            asyncio.get_running_loop().create_task(_deliver(items))
        except RuntimeError:
            pass  # no event loop (sync scripts): nothing to push

    @event.listens_for(Session, "after_rollback")
    def _drop(session):
        session.info.pop("web_push", None)


async def _deliver(items: list[dict]) -> None:
    from app.db.session import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            for item in items:
                await send_to_users(db, [item["user_id"]], item)
    except Exception:
        log.warning("web push delivery failed", exc_info=True)
