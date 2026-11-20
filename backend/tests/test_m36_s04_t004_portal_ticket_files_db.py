"""M36.S04.T004 customer self-service tickets on disposable PostgreSQL: attachments from the portal and
from staff (scan gate, sharing approval, customer isolation) and portal replies feeding the CRM inbox."""
from __future__ import annotations

import io
import os
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.datastructures import Headers

from app.api.v1.endpoints import helpdesk as staff_api
from app.api.v1.endpoints import portal_self as portal_api
from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMConversation
from app.models.helpdesk import HelpdeskTicket, TicketAttachment, TicketComment
from app.models.portal import PortalAccount, PortalAccountStatus, PortalUser
from app.models.sales import Customer, CustomerChannel
from app.models.user import User
from app.services import crm_inbox_service as inbox
from app.services import document_storage_service as storage_svc

TASK_DB_ENV = "M36_S04_T004_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S04_T004_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s04_t004_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")

PDF = b"%PDF-1.4\n% POVU delivery note\n%%EOF\n"


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _upload(name: str, data: bytes, ctype: str) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=name, headers=Headers({"content-type": ctype}))


def _staff(uid, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, is_superuser=False, access_scopes=[],
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_portal_ticket_files_and_replies(monkeypatch, tmp_path):
    s = uuid4().hex[:8]
    verdict = {"status": "CLEAN"}

    async def fake_scan(path):
        return storage_svc.ScanResult(verdict["status"], "test scanner")

    monkeypatch.setattr(storage_svc, "scan_document", fake_scan)
    monkeypatch.setattr(storage_svc.settings, "DOCUMENT_STORAGE_PATH", str(tmp_path))
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        a = Customer(code=f"PA-{s}", name="Mama Duka", channel=CustomerChannel.RETAIL, currency="KES")
        b = Customer(code=f"PB-{s}", name="Other Shop", channel=CustomerChannel.RETAIL, currency="KES")
        agent = User(email=f"qa-{s}@povu.example", username=f"qa{s}", full_name="QC agent", hashed_password="x")
        db.add_all([a, b, agent])
        await db.flush()
        users = {}
        for key, cust in (("a", a), ("b", b)):
            acc = PortalAccount(account_code=f"P{key.upper()}-{s}", linked_customer_id=str(cust.id), portal_status=PortalAccountStatus.ACTIVE)
            db.add(acc)
            await db.flush()
            pu = PortalUser(portal_account_id=acc.id, full_name=f"Buyer {key}", email=f"buyer-{key}-{s}@shops.example")
            db.add(pu)
            await db.flush()
            users[key] = pu.id
        t = HelpdeskTicket(ticket_no=f"TKT-{s}", subject="Broken caps", customer_id=a.id)
        db.add(t)
        await db.commit()
        tid, agent_id = t.id, agent.id

    async def portal_user(db, key):
        return (await db.execute(select(PortalUser).options(selectinload(PortalUser.account))
                                 .where(PortalUser.id == users[key]))).scalar_one()

    qc = _staff(agent_id, "quality.view", "quality.edit")
    async with AsyncSessionLocal() as db:
        ua, ub = await portal_user(db, "a"), await portal_user(db, "b")
        mine = await portal_api.add_ticket_file(tid, _upload("caps.pdf", PDF, "application/pdf"), ua, db)
        assert mine["from_customer"] and mine["downloadable"]
        with pytest.raises(HTTPException) as e:                       # another customer: not their ticket
            await portal_api.add_ticket_file(tid, _upload("x.pdf", PDF, "application/pdf"), ub, db)
        assert e.value.status_code == 404
        with pytest.raises(HTTPException) as e:
            await portal_api.get_ticket_file(tid, __import__("uuid").UUID(mine["id"]), ub, db)
        assert e.value.status_code == 404
        with pytest.raises(HTTPException) as e:                       # disguised file type
            await portal_api.add_ticket_file(tid, _upload("caps.pdf", b"MZ not a pdf", "application/pdf"), ua, db)
        assert e.value.status_code == 415
        verdict["status"] = "INFECTED"
        with pytest.raises(HTTPException) as e:
            await portal_api.add_ticket_file(tid, _upload("evil.pdf", PDF, "application/pdf"), ua, db)
        assert e.value.status_code == 422
        await db.rollback()
        ua = await portal_user(db, "a")                                # objects expire on rollback
        verdict["status"] = "NOT_SCANNED"
        quarantined = await portal_api.add_ticket_file(tid, _upload("photo.pdf", PDF, "application/pdf"), ua, db)
        assert quarantined["downloadable"] is False

        # staff: sees both, can download only the clean one; their own file reaches the customer only when shared
        with pytest.raises(HTTPException) as e:
            await staff_api.list_ticket_files(tid, db, _staff(agent_id, "sales.view"))
        assert e.value.status_code == 403
        listed = await staff_api.list_ticket_files(tid, db, qc)
        assert {x["file_name"] for x in listed} == {"caps.pdf", "photo.pdf"}
        from uuid import UUID
        assert (await staff_api.download_ticket_file(UUID(mine["id"]), db, qc)).status_code == 200
        with pytest.raises(HTTPException) as e:
            await staff_api.download_ticket_file(UUID(quarantined["id"]), db, qc)
        assert e.value.status_code == 409
        verdict["status"] = "CLEAN"
        note = await staff_api.add_ticket_file(tid, _upload("credit-note.pdf", PDF, "application/pdf"), False, db, qc)
        seen = {x["file_name"] for x in (await portal_api.ticket(tid, ua, db))["attachments"]}
        assert "credit-note.pdf" not in seen and {"caps.pdf", "photo.pdf"} <= seen
        await staff_api.share_ticket_file(UUID(note["id"]), True, db, qc)
        portal_view = await portal_api.ticket(tid, ua, db)
        assert "credit-note.pdf" in {x["file_name"] for x in portal_view["attachments"]}
        assert all("customer_visible" not in x for x in portal_view["attachments"])
        assert (await portal_api.get_ticket_file(tid, UUID(note["id"]), ua, db)).status_code == 200
        with pytest.raises(HTTPException) as e:
            await staff_api.share_ticket_file(UUID(mine["id"]), False, db, qc)   # customer's own file stays theirs
        assert e.value.status_code == 409
        assert (await db.execute(select(func.count()).select_from(TicketAttachment)
                                 .where(TicketAttachment.ticket_id == tid))).scalar_one() == 3

    # CRM inbox: a staff reply answers the ticket; the customer's portal reply makes it unread and due again
    rep = SimpleNamespace(id=agent_id, is_superuser=True, access_scopes=[], roles=[], company_id=None)
    async with AsyncSessionLocal() as db:
        db.add(TicketComment(ticket_id=tid, body="We will replace the 2 cartons.", is_internal=False, created_by_id=agent_id))
        await db.commit()
        await inbox.sync(db)
        await db.commit()
        conv = (await db.execute(select(CRMConversation).where(CRMConversation.source_ref == str(tid)))).scalar_one()
        assert conv.sla_due_at is None                                # answered
        await inbox.mark_read(db, rep, conv)
        await db.commit()
        ua = await portal_user(db, "a")
        await portal_api.reply(tid, portal_api.ReplyIn(body="Still waiting for the cartons"), ua, db)
        out = await inbox.list_conversations(db, rep, channel="TICKET")
        row = next(i for i in out["items"] if i["id"] == str(conv.id))
        assert row["unread"] and row["sla_due_at"] is not None       # customer wrote again
