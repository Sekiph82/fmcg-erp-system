"""Real malware scanning acceptance (ClamAV over clamd INSTREAM) for partner and field uploads, on disposable PostgreSQL.

Needs a local ClamAV daemon (e.g. `docker run -p 127.0.0.1:3310:3310 clamav/clamav:stable`) given as CLAMAV_TEST_HOST.
The EICAR anti-virus test string (harmless, recognised by every scanner) is assembled in memory only.
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.deps import get_current_user
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Supplier
from app.models.procurement import POLine, POStatus, PurchaseOrder
from app.models.supplier_portal import SPAccount, SPAccountStatus, SPDocument, SPUser, SPUserRole

TASK_DB_ENV = "M38_AV_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M38_AV_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m38_av_[a-f0-9]{24}")
CLAMAV = os.environ.get("CLAMAV_TEST_HOST", "")
pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1" or not CLAMAV.startswith("127.0.0.1"),
                                reason="requires the task-owned disposable PostgreSQL and a local ClamAV daemon")
PW = "Supplier-Pass-2026"
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _eicar() -> bytes:
    parts = ["X5O!P%@AP[4\\PZX54(P^)7CC)7}$", "EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"]
    return "".join(parts).encode()


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_clamav_quarantines_infected_and_releases_clean(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.main import app
    from app.services.document_storage_service import scan_document

    host, port = CLAMAV.split(":")
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr(settings, "DOCUMENT_CLAMAV_HOST", host)
    monkeypatch.setattr(settings, "DOCUMENT_CLAMAV_PORT", int(port))

    # the scanner itself
    clean_file, bad_file = tmp_path / "clean.pdf", tmp_path / "bad.txt"
    clean_file.write_bytes(PDF)
    bad_file.write_bytes(_eicar())
    assert (await scan_document(clean_file)).status == "CLEAN"
    assert (await scan_document(bad_file)).status == "INFECTED"
    bad_file.unlink()

    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        sup = Supplier(code=f"AV-{s}", name=f"AV Co {s}")
        db.add(sup)
        await db.flush()
        acc = SPAccount(supplier_id=sup.id, portal_status=SPAccountStatus.ACTIVE)
        db.add(acc)
        await db.flush()
        db.add(SPUser(account_id=acc.id, full_name="Sam", email=f"sam-{s}@example.com", password_hash=hash_password(PW),
                      role_type=SPUserRole.OWNER, is_active=True))
        await db.commit()
        acc_id = acc.id

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.post("/api/v1/supplier-self/auth/login", json={"email": f"sam-{s}@example.com", "password": PW})).status_code == 200
        bad = await c.post("/api/v1/supplier-self/documents", data={"upload_type": "OTHER"},
                           files={"file": ("notes.txt", _eicar(), "text/plain")})
        assert bad.status_code == 422 and "malware" in bad.text                      # refused, nothing stored
        ok = await c.post("/api/v1/supplier-self/documents", data={"upload_type": "INVOICE"},
                          files={"file": ("invoice.pdf", PDF, "application/pdf")})
        assert ok.status_code == 201, ok.text
    assert [f.name for f in tmp_path.iterdir() if re.fullmatch(r"[0-9a-f]{32}", f.name)].__len__() == 1  # only the clean file

    async with AsyncSessionLocal() as db:
        doc = (await db.execute(select(SPDocument).where(SPDocument.account_id == acc_id))).scalar_one()
        assert doc.scan_status == "CLEAN"
        doc_id = doc.id
    staff = SimpleNamespace(id=uuid.uuid4(), username="buyer", email="b@example.com", full_name="B", is_superuser=False,
                            is_active=True, access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, access_scopes=[],
                            permissions=[SimpleNamespace(code="procurement.view", module="procurement", action="view", is_active=True)])])
    app.dependency_overrides[get_current_user] = lambda: staff
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get(f"/api/v1/supplier-portal/documents/{doc_id}/file")
            assert r.status_code == 200 and r.content == PDF                           # CLEAN files are released to staff
    finally:
        app.dependency_overrides.pop(get_current_user, None)
