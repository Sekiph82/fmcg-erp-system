"""M38 supplier self-service portal on disposable PostgreSQL through the real app: staff invite link → activation,
supplier realm sign-in, only own released POs, acknowledge/ETA/document upload by role, payment visibility, the removed
unauthenticated password reset, and staff permission gate."""
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
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Supplier
from app.models.procurement import POLine, POStatus, PurchaseOrder
from app.models.supplier_portal import SPAccount, SPAccountStatus, SPDocument, SPPOResponse

TASK_DB_ENV = "M38_S05_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M38_S05_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m38_s05_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")
API = "/api/v1/supplier-self"
PW = "Supplier-Pass-2026"
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


def _staff(*codes):
    return SimpleNamespace(id=uuid.uuid4(), username="buyer", email="b@example.com", full_name="B", is_superuser=False,
                           is_active=True, access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, access_scopes=[],
                           permissions=[SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".")[1], is_active=True)
                                        for c in codes])])


@pytest.mark.asyncio
async def test_supplier_portal_end_to_end(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path))
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        ours, theirs = Supplier(code=f"SUP-{s}", name=f"Sugar Co {s}"), Supplier(code=f"OTH-{s}", name=f"Other {s}")
        db.add_all([ours, theirs])
        await db.flush()
        pos = {}
        for key, sup, st in (("open", ours, POStatus.ORDERED), ("draft", ours, POStatus.DRAFT), ("other", theirs, POStatus.ORDERED)):
            po = PurchaseOrder(po_no=f"PO-{key}-{s}", supplier_id=sup.id, order_date=date.today(),
                               expected_delivery_date=date.today() + timedelta(days=7), currency="KES", status=st)
            db.add(po)
            await db.flush()
            db.add(POLine(po_id=po.id, line_no=1, description="Cane sugar 50kg", ordered_quantity=Decimal("40"),
                          unit="BAG", unit_price=Decimal("3500")))
            pos[key] = po.id
        acc = SPAccount(supplier_id=ours.id, portal_status=SPAccountStatus.ACTIVE, can_view_payment=True)
        db.add(acc)
        await db.commit()
        acc_id = acc.id

    try:
        async with _client(app) as st:
            app.dependency_overrides[get_current_user] = lambda: _staff("sales.view")
            assert (await st.get("/api/v1/supplier-portal/accounts")).status_code == 403          # needs procurement
            assert (await st.post("/api/v1/supplier-portal/auth/reset-password",
                                  json={"email": "x@example.com", "new_password": "p"})).status_code in (404, 405)
            app.dependency_overrides[get_current_user] = lambda: _staff("procurement.view", "procurement.edit")
            links = {}
            for role in ("SALES", "VIEWER"):
                r = await st.post(f"/api/v1/supplier-portal/accounts/{acc_id}/users/invite",
                                  json={"full_name": role, "email": f"{role.lower()}-{s}@Example.com", "role_type": role})
                assert r.status_code == 200, r.text
                links[role] = r.json()["activation_link"].split("token=")[1]
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    async with _client(app) as anon:
        assert (await anon.post(f"{API}/auth/login", json={"email": f"sales-{s}@example.com", "password": PW})).status_code == 401
        for role, t in links.items():
            assert (await anon.post(f"{API}/auth/activate", json={"token": t, "new_password": PW})).status_code == 200
        assert (await anon.post(f"{API}/auth/activate", json={"token": links["SALES"], "new_password": PW})).status_code == 400

    async with _client(app) as c:
        r = await c.post(f"{API}/auth/login", json={"email": f"SALES-{s}@example.com", "password": PW})
        assert r.status_code == 200 and r.json()["supplier_name"] == f"Sugar Co {s}" and r.json()["can_respond"]
        assert "erp_supplier_token" in c.cookies
        assert (await c.get("/api/v1/supplier-portal/accounts")).status_code == 401              # not a staff session
        assert (await c.get("/api/v1/portal-self/me")).status_code == 401                        # not a distributor session
        listed = (await c.get(f"{API}/purchase-orders")).json()
        assert [p["po_number"] for p in listed] == [f"PO-open-{s}"] and listed[0]["total_amount"] == 140000.0
        assert (await c.get(f"{API}/purchase-orders/{pos['draft']}")).status_code == 404
        assert (await c.get(f"{API}/purchase-orders/{pos['other']}")).status_code == 404
        detail = (await c.get(f"{API}/purchase-orders/{pos['open']}")).json()
        assert detail["lines"][0]["item"] == "Cane sugar 50kg" and detail["acknowledgment"] is None
        assert (await c.post(f"{API}/purchase-orders/{pos['other']}/acknowledge", json={"response_status": "ACCEPTED"})).status_code == 404
        assert (await c.post(f"{API}/purchase-orders/{pos['open']}/acknowledge", json={"response_status": "REJECTED"})).status_code == 422
        assert (await c.post(f"{API}/purchase-orders/{pos['open']}/acknowledge",
                             json={"response_status": "ACCEPTED", "supplier_comment": "OK"})).json()["status"] == "ACCEPTED"
        eta = {"proposed_date": (date.today() + timedelta(days=9)).isoformat(), "supplier_reason": "Port congestion"}
        assert (await c.post(f"{API}/purchase-orders/{pos['other']}/eta", json=eta)).status_code == 404
        assert (await c.post(f"{API}/purchase-orders/{pos['open']}/eta", json=eta)).json()["revision_no"] == 1
        up = await c.post(f"{API}/documents", data={"upload_type": "INVOICE", "linked_po_id": str(pos["open"])},
                          files={"file": ("inv.pdf", PDF, "application/pdf")})
        assert up.status_code == 201, up.text
        bad = await c.post(f"{API}/documents", data={"upload_type": "INVOICE", "linked_po_id": str(pos["other"])},
                           files={"file": ("inv.pdf", PDF, "application/pdf")})
        assert bad.status_code == 422
        exe = await c.post(f"{API}/documents", data={"upload_type": "OTHER"}, files={"file": ("x.exe", b"MZ\x90\x00", "application/octet-stream")})
        assert exe.status_code == 415
        assert [d["file_name"] for d in (await c.get(f"{API}/documents")).json()] == ["inv.pdf"]
        assert (await c.get(f"{API}/payments")).status_code == 403                               # SALES role
    async with _client(app) as v:
        assert (await v.post(f"{API}/auth/login", json={"email": f"viewer-{s}@example.com", "password": PW})).status_code == 200
        assert (await v.post(f"{API}/purchase-orders/{pos['open']}/acknowledge", json={"response_status": "ACCEPTED"})).status_code == 403
        assert (await v.get(f"{API}/purchase-orders")).status_code == 200

    async with AsyncSessionLocal() as db:
        resp = (await db.execute(select(SPPOResponse).where(SPPOResponse.po_id == pos["open"]))).scalar_one()
        assert resp.response_status.value == "ACCEPTED"
        doc = (await db.execute(select(SPDocument).where(SPDocument.account_id == acc_id))).scalar_one()
        assert re.fullmatch(r"[0-9a-f]{32}", doc.file_path) and (tmp_path / doc.file_path).read_bytes() == PDF
