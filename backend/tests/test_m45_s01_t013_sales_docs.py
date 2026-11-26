"""M45.S01.T013 sales document library (DB part needs M45_DB=1), through real sessions and the public routes.

Approved SALES_DOCUMENT with a clean scan: share → public meta shows version and SHA-256 → view recorded once per
30 minutes → download recorded; a NOT_SCANNED file is never served (423); a link follows the newest approved version
unless pinned; revoked/expired → 410; unknown token 404; a draft or another category cannot be shared; one link never
serves another document.
"""
import hashlib
import os
import uuid
from datetime import timedelta

import httpx
import pytest

DB = pytest.mark.skipif(os.environ.get("M45_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M45_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


@DB
@pytest.mark.asyncio
async def test_share_view_download_versions(tmp_path, monkeypatch):
    from sqlalchemy import select
    from app.core.config import settings
    from app.core.security import hash_password
    from app.db.session import AsyncSessionLocal
    from app.models.documents import Document, DocumentCategory, DocumentStatus
    from app.models.payments_hub import DocShareEvent, DocShareLink
    from app.models.user import User
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path))
    from app.services import document_storage_service as dss
    storage = dss.get_document_storage()
    content = b"%PDF-1.4 POVU price list v1"
    key1, key2 = uuid.uuid4().hex, uuid.uuid4().hex
    storage.path_for(key1).parent.mkdir(parents=True, exist_ok=True)
    storage.path_for(key1).write_bytes(content)
    storage.path_for(key2).write_bytes(b"%PDF-1.4 POVU price list v2")
    pw = uuid.uuid4().hex + "Aa1!"
    async with AsyncSessionLocal() as db:
        from app.models.role import Permission, Role
        u = User(username=f"rep-{uuid.uuid4().hex[:6]}", email=f"{uuid.uuid4().hex[:6]}@povu-demo.test", full_name="Rep",
                 hashed_password=hash_password(pw), is_active=True)
        role = Role(name=f"docs-{uuid.uuid4().hex[:6]}", is_active=True)
        for code in ("documents.view", "documents.create"):
            p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
            if p is None:
                p = Permission(code=code, name=code, module="documents", action=code.split(".")[1], is_active=True)
                db.add(p)
            role.permissions.append(p)
        u.roles.append(role)
        db.add(role)
        lin = uuid.uuid4()
        v1 = Document(id=lin, title="POVU price list", category=DocumentCategory.SALES_DOCUMENT, version=1, status=DocumentStatus.APPROVED,
                      is_latest=False, lineage_id=lin, file_name="price-list.pdf", mime_type="application/pdf", storage_provider="local",
                      storage_key=key1, file_checksum_sha256=hashlib.sha256(content).hexdigest(), file_scan_status="CLEAN", file_size_bytes=len(content))
        v2 = Document(title="POVU price list", category=DocumentCategory.SALES_DOCUMENT, version=2, status=DocumentStatus.APPROVED,
                      is_latest=True, lineage_id=lin, previous_version_id=lin, file_name="price-list-v2.pdf", mime_type="application/pdf",
                      storage_provider="local", storage_key=key2, file_checksum_sha256="b" * 64, file_scan_status="NOT_SCANNED")
        draft = Document(title="Draft proposal", category=DocumentCategory.SALES_DOCUMENT, version=1, status=DocumentStatus.DRAFT, is_latest=True)
        other = Document(title="HR file", category=DocumentCategory.HR_DOCUMENT, version=1, status=DocumentStatus.APPROVED, is_latest=True)
        db.add_all([u, v1, v2, draft, other])
        await db.commit()
        ids = {"v1": v1.id, "v2": v2.id, "draft": draft.id, "other": other.id, "user": u.username}
    async with _client() as c:
        assert (await c.post("/api/v1/auth/login", data={"username": ids["user"], "password": pw})).status_code == 200
        assert (await c.post(f"/api/v1/sales-docs/{ids['draft']}/share", json={})).status_code == 409
        assert (await c.post(f"/api/v1/sales-docs/{ids['other']}/share", json={})).status_code == 404
        pinned = (await c.post(f"/api/v1/sales-docs/{ids['v1']}/share", json={"pin_version": True, "label": "Duka Moja"})).json()
        latest = (await c.post(f"/api/v1/sales-docs/{ids['v1']}/share", json={})).json()
        t_pin, t_latest = pinned["url"].rsplit("/", 1)[1], latest["url"].rsplit("/", 1)[1]
        m = (await c.get(f"/api/v1/public/docs/{t_pin}")).json()
        assert m["version"] == 1 and m["sha256"] == hashlib.sha256(content).hexdigest() and m["available"]
        assert (await c.post(f"/api/v1/public/docs/{t_pin}/view")).json() == {"recorded": True}
        assert (await c.post(f"/api/v1/public/docs/{t_pin}/view")).json() == {"recorded": False}      # 30-minute de-dupe
        f = await c.get(f"/api/v1/public/docs/{t_pin}/file")
        assert f.status_code == 200 and f.content == content
        ml = (await c.get(f"/api/v1/public/docs/{t_latest}")).json()
        assert ml["version"] == 2 and not ml["available"]                                            # newest approved, not scanned
        assert (await c.get(f"/api/v1/public/docs/{t_latest}/file")).status_code == 423
        assert (await c.get(f"/api/v1/public/docs/{'z' * 43}")).status_code == 404
        await c.post(f"/api/v1/sales-docs/links/{pinned['id']}/revoke")
        assert (await c.get(f"/api/v1/public/docs/{t_pin}")).status_code == 410
        stats = {l["id"]: l for l in (await c.get(f"/api/v1/sales-docs/{ids['v1']}/links")).json()}
        assert stats[pinned["id"]]["views"] == 1 and stats[pinned["id"]]["downloads"] == 1 and stats[pinned["id"]]["revoked"]
    async with AsyncSessionLocal() as db:                                  # a newer version made confidential stops the link
        v2 = await db.get(Document, ids["v2"])
        v2.confidentiality_level = "CONFIDENTIAL"
        await db.commit()
    async with _client() as c:
        assert (await c.get(f"/api/v1/public/docs/{t_latest}")).status_code == 410
    async with AsyncSessionLocal() as db:
        l = await db.get(DocShareLink, uuid.UUID(latest["id"]))
        l.expires_at = l.created_at - timedelta(seconds=1)
        await db.commit()
        ev = (await db.execute(select(DocShareEvent).where(DocShareEvent.kind == "DOWNLOAD"))).scalars().first()
        assert ev.document_id == ids["v1"]
    async with _client() as c:
        assert (await c.get(f"/api/v1/public/docs/{t_latest}")).status_code == 410
