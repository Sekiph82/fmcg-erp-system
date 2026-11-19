"""Registered employee e-signatures on disposable PostgreSQL through the real app: IT registers, each person
sees only their own, IT sees metadata only, signing applies the registered signature, replace/revoke history."""
from __future__ import annotations

import base64
import os
import re
import uuid
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.deps import get_current_user
from app.db.session import AsyncSessionLocal, engine
from app.models.esign import (
    SignatureRecord, SignatureRecordStatus, SignatureRequest, SignatureRequestStatus, UserSignatureProfile,
)
from app.models.user import User

TASK_DB_ENV = "ESIGN_SIG_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "ESIGN_SIG_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_esign_sig_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")

PNG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode()
PNG2 = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x01" * 64).decode()


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _as(user, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=user.id, username=user.username, email=user.email, full_name=user.full_name,
                           is_superuser=False, is_active=True, access_scopes=[],
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_it_registers_each_user_sees_only_own_and_signing_uses_it():
    from app.main import app

    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        it, ali, ayse = [User(email=f"{n}-{s}@example.invalid", username=f"{n}{s}", full_name=f"{n.title()} {s}",
                              hashed_password="x") for n in ("it", "ali", "ayse")]
        db.add_all([it, ali, ayse])
        await db.flush()
        req = SignatureRequest(request_no=f"SR-{s}", document_type="contract", document_ref=f"C-{s}", requester_id=it.id,
                               subject="Supply contract", status=SignatureRequestStatus.PENDING, required_count=1)
        db.add(req)
        await db.flush()
        db.add(SignatureRecord(request_id=req.id, signer_id=ali.id, status=SignatureRecordStatus.PENDING))
        req2 = SignatureRequest(request_no=f"SR2-{s}", document_type="contract", document_ref=f"C2-{s}", requester_id=it.id,
                                subject="Second", status=SignatureRequestStatus.PENDING, required_count=1)
        db.add(req2)
        await db.flush()
        db.add(SignatureRecord(request_id=req2.id, signer_id=ali.id, status=SignatureRecordStatus.PENDING))
        await db.commit()
        req2_id = req2.id
        IT, ALI, AYSE, req_id = _as(it, "esign.admin", "esign.view"), _as(ali, "esign.view", "esign.sign"), _as(ayse, "esign.view"), req.id

    def who(u):
        app.dependency_overrides[get_current_user] = lambda: u

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            who(ALI)
            assert (await c.put(f"/api/v1/esign/signatures/{ALI.id}", json={"signature_image": PNG})).status_code == 403  # only IT
            who(IT)
            fake = "data:image/png;base64," + base64.b64encode(b"<svg onload=alert(1)>" * 3).decode()
            assert (await c.put(f"/api/v1/esign/signatures/{ALI.id}", json={"signature_image": fake})).status_code == 422
            assert (await c.put(f"/api/v1/esign/signatures/{ALI.id}", json={"signature_image": PNG})).status_code == 200
            listing = {r["user_id"]: r for r in (await c.get(f"/api/v1/esign/signatures?search={s}")).json()}
            assert listing[str(ALI.id)]["has_signature"] and not listing[str(AYSE.id)]["has_signature"]
            assert all("signature_image" not in r for r in listing.values())                       # IT: metadata only
            assert (await c.get("/api/v1/esign/my-signature")).json() == {"has_signature": False}   # IT's own: none

            who(ALI)
            mine = (await c.get("/api/v1/esign/my-signature")).json()
            assert mine["has_signature"] and mine["signature_image"] == PNG
            who(AYSE)
            assert (await c.get("/api/v1/esign/my-signature")).json() == {"has_signature": False}  # never Ali's
            assert (await c.get("/api/v1/esign/signatures")).status_code == 403

            who(ALI)  # signs without drawing: the registered signature is applied
            assert (await c.post(f"/api/v1/esign/requests/{req_id}/sign", json={})).status_code == 200
            own = (await c.get(f"/api/v1/esign/requests/{req_id}")).json()["signature_records"][0]["signature_data"]
            assert own == PNG                                                    # the signer sees their own
            for viewer in (IT, AYSE):                                            # requester/admin and other viewers never
                who(viewer)
                recs = (await c.get(f"/api/v1/esign/requests/{req_id}")).json().get("signature_records", [])
                assert all(r["signature_data"] is None for r in recs)

            who(IT)  # replace keeps history; revoke stops further use
            assert (await c.put(f"/api/v1/esign/signatures/{ALI.id}", json={"signature_image": PNG2})).status_code == 200
            assert (await c.delete(f"/api/v1/esign/signatures/{ALI.id}?reason=left%20the%20company")).status_code == 200
            who(ALI)
            assert (await c.get("/api/v1/esign/my-signature")).json() == {"has_signature": False}
            assert (await c.post(f"/api/v1/esign/requests/{req2_id}/sign", json={"signature_data": PNG2})).status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    async with AsyncSessionLocal() as db:
        rec = (await db.execute(select(SignatureRecord).where(SignatureRecord.request_id == req_id))).scalar_one()
        assert rec.status == SignatureRecordStatus.SIGNED and rec.signature_data == PNG
        assert rec.auth_method.startswith("registered-signature:")
        history = (await db.execute(select(UserSignatureProfile).where(UserSignatureProfile.user_id == ALI.id)
                                    .order_by(UserSignatureProfile.registered_at))).scalars().all()
        assert [(h.is_active, h.revoke_reason) for h in history] == [(False, "replaced"), (False, "left the company")]
