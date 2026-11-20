"""M36.S03.T003 mobile quick notes on disposable PostgreSQL: idempotent create (phone retries), permissions,
profile auto-creation and the note on the customer timeline."""
from __future__ import annotations

import os
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints import crm_pipeline as api
from app.db.session import AsyncSessionLocal, engine
from app.models.marketing import CRMProfile, CustomerInteraction
from app.models.sales import Customer, CustomerChannel
from app.models.user import User
from app.services import customer_timeline_service as tl

TASK_DB_ENV = "M36_S03_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S03_T003_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s03_t003_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(uid, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, is_superuser=False, access_scopes=[],
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_quick_note_idempotent_and_on_timeline():
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        cust = Customer(code=f"QN-{s}", name="Mama Duka", channel=CustomerChannel.RETAIL, currency="KES")
        rep_row = User(email=f"qn-{s}@povu.example", username=f"qn{s}", full_name="Rep", hashed_password="x")
        db.add_all([cust, rep_row])
        await db.commit()
        cid, rep = str(cust.id), _user(rep_row.id, "crm.view_all", "crm.create_all")

        body = api.QuickNoteIn(channel="visit", summary="Shelf has 3 cartons POVU AllClean 1 L left; wants 20 more on Friday",
                               client_ref=f"phone-{s}-0001-aaaa")
        first = await api.customer_quick_note(cid, body, db, rep)
        again = await api.customer_quick_note(cid, body, db, rep)          # retry after a dropped connection
        assert first["duplicate"] is False and again == {"id": first["id"], "duplicate": True}
        await api.customer_quick_note(cid, api.QuickNoteIn(channel="call", summary="Called about payment", client_ref=f"phone-{s}-0002-aaaa"), db, rep)
        n = (await db.execute(select(func.count()).select_from(CustomerInteraction)
                              .join(CRMProfile, CRMProfile.id == CustomerInteraction.crm_profile_id)
                              .where(CRMProfile.customer_id == cust.id))).scalar_one()
        assert n == 2
        assert (await db.execute(select(func.count()).select_from(CRMProfile).where(CRMProfile.customer_id == cust.id))).scalar_one() == 1

        other = User(email=f"qn2-{s}@povu.example", username=f"qn2{s}", full_name="Other", hashed_password="x")
        db.add(other)
        await db.commit()
        with pytest.raises(HTTPException) as e:                            # another user reusing the key: refused, not leaked
            await api.customer_quick_note(cid, body, db, _user(other.id, "crm.view_all", "crm.create_all"))
        assert e.value.status_code == 409 and first["id"] not in str(e.value.detail)
        with pytest.raises(HTTPException) as e:                            # no scope over the customer
            await api.customer_quick_note(cid, api.QuickNoteIn(summary="x" * 5, client_ref=f"phone-{s}-0003-aaaa"), db, _user(rep_row.id, "hr.view"))
        assert e.value.status_code == 403

        page = await tl.timeline(db, cust.id, rep, 20)
        details = [e.get("detail") for e in page["events"] if e["type"] == "interaction"]
        assert any("POVU AllClean" in (d or "") for d in details) and len(details) == 2
