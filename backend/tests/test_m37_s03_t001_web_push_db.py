"""M37.S03.T001 Web Push on disposable PostgreSQL: RFC 8291 payloads decrypt with the browser's key, VAPID JWTs verify
with the published key, delivery removes gone subscriptions, new notifications are pushed after commit, and the
admin-only mobile routes are locked."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import struct
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import HTTPException
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.mobile import WebPushSubscription
from app.models.user import User
from app.services import web_push_service as wp

TASK_DB_ENV = "M37_S03_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M37_S03_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m37_s03_t001_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _browser():
    key = ec.generate_private_key(ec.SECP256R1())
    pub = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = os.urandom(16)
    return key, wp.b64u(pub), wp.b64u(auth)


def _decrypt(body: bytes, ua_key, auth_b64: str) -> bytes:
    """What the browser does (RFC 8291)."""
    salt, rs, idlen = body[:16], struct.unpack(">I", body[16:20])[0], body[20]
    as_pub = body[21:21 + idlen]
    ct = body[21 + idlen:]
    assert rs == 4096
    ua_pub = ua_key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    shared = ua_key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
    hk = lambda s, i, k, n: HKDF(algorithm=hashes.SHA256(), length=n, salt=s, info=i).derive(k)  # noqa: E731
    ikm = hk(wp.unb64u(auth_b64), b"WebPush: info\x00" + ua_pub + as_pub, shared, 32)
    plain = AESGCM(hk(salt, b"Content-Encoding: aes128gcm\x00", ikm, 16)).decrypt(hk(salt, b"Content-Encoding: nonce\x00", ikm, 12), ct, None)
    assert plain.endswith(b"\x02")
    return plain[:-1]


def _verify_vapid(header: str, public_b64: str, endpoint: str):
    t = re.search(r"t=([^,]+)", header).group(1)
    k = re.search(r"k=(\S+)", header).group(1)
    assert k == public_b64
    head, claims, sig = t.split(".")
    raw = wp.unb64u(sig)
    pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), wp.unb64u(k))
    pub.verify(encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
               f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))
    c = json.loads(wp.unb64u(claims))
    assert c["aud"] == "https://push.example" and c["exp"] > 0 and c["sub"]


@pytest.mark.asyncio
async def test_web_push_crypto_delivery_hook_and_locks():
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        wp._vapid_cache = None
        u = User(email=f"wp-{s}@povu.example", username=f"wp{s}", full_name="Phone User", hashed_password="x")
        db.add(u)
        await db.commit()
        uid = u.id

        # VAPID key is created once and stable
        k1 = (await wp.vapid_keys(db))[1]
        wp._vapid_cache = None
        assert (await wp.vapid_keys(db))[1] == k1

        ua_key, p256dh, auth = _browser()
        gone_key, gp, ga = _browser()
        db.add_all([WebPushSubscription(user_id=uid, endpoint=f"https://push.example/ok-{s}", p256dh=p256dh, auth=auth),
                    WebPushSubscription(user_id=uid, endpoint=f"https://push.example/gone-{s}", p256dh=gp, auth=ga)])
        await db.commit()

        seen = []

        def handler(req: httpx.Request):
            assert req.headers["content-encoding"] == "aes128gcm" and int(req.headers["ttl"]) > 0
            _verify_vapid(req.headers["authorization"], k1, str(req.url))
            if "gone" in str(req.url):
                return httpx.Response(410)
            seen.append(json.loads(_decrypt(req.content, ua_key, auth)))
            return httpx.Response(201)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            out = await wp.send_to_users(db, [str(uid)], {"title": "PO approved", "body": "SYNTH-PO-0001 for POVU AllClean", "url": "/dashboard"}, client=client)
        assert out == {"sent": 1, "failed": 0, "removed": 1}
        assert seen == [{"title": "PO approved", "body": "SYNTH-PO-0001 for POVU AllClean", "url": "/dashboard", "tag": None}]
        assert (await db.execute(select(func.count()).select_from(WebPushSubscription).where(WebPushSubscription.user_id == uid))).scalar_one() == 1

        # every new in-app notification is pushed after commit (and not on rollback)
        from app.models.notifications import Notification, NotificationType
        delivered = []

        async def fake_deliver(items):
            delivered.extend(items)
        orig = wp._deliver
        wp._deliver = fake_deliver
        try:
            wp.install_notification_hook()
            db.add(Notification(user_id=str(uid), title="Leave approved", message="Your leave 1-3 Dec is approved",
                                notification_type=list(NotificationType)[0]))
            await db.commit()
            await asyncio.sleep(0.05)
            db.add(Notification(user_id=str(uid), title="rolled back", message="x", notification_type=list(NotificationType)[0]))
            await db.flush()
            await db.rollback()
            await asyncio.sleep(0.05)
        finally:
            wp._deliver = orig
        assert [d["title"] for d in delivered] == ["Leave approved"]

    # bad subscriptions are refused; admin-only routes are locked
    from app.api.v1.endpoints import mobile
    with pytest.raises(HTTPException):
        await mobile.web_push_subscribe(mobile.WebPushSubscribeIn(endpoint="http://insecure.example/x", keys=mobile.WebPushKeys(p256dh=p256dh, auth=auth)),
                                        SimpleNamespace(headers={}), None, SimpleNamespace(id=uid))
    perms = [SimpleNamespace(code="crm.view", module="crm", action="view", is_active=True)]
    plain = SimpleNamespace(id=uid, is_superuser=False, roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])], access_scopes=[])
    with pytest.raises(HTTPException) as e:
        await mobile.MOBILE_ADMIN(plain)
    assert e.value.status_code == 403
