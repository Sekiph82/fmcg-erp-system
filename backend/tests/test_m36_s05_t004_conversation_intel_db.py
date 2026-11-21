"""M36.S05.T004 conversation intelligence on disposable PostgreSQL: opt-in and consent gates, access control,
every finding quoted verbatim from the source, no invented scores, and the coaching review workflow."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints import conversation_intel as api
from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMChatMessage, CRMChatSession
from app.models.user import User
from app.models.voip import CallLog
from app.services import conversation_intel_service as ci

TASK_DB_ENV = "M36_S05_T004_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S05_T004_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s05_t004_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")

TRANSCRIPT = ("Agent: Good morning, this is POVU sales. Customer: The POVU AllClean price is too expensive this month. "
              "Customer: Can you deliver on Saturday? Customer: Also the last delivery was late by two days. "
              "Agent: I will send you the price list tomorrow and call back next week.")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(uid, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, is_superuser=False, access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_conversation_intelligence(monkeypatch):
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        rows = [User(email=f"{n}-{s}@povu.example", username=f"{n}{s}", full_name=n, hashed_password="x") for n in ("ann", "ben", "mgr")]
        db.add_all(rows)
        await db.flush()
        call = CallLog(call_ref=f"CALL-{s}", phone_number="+254700000001", agent_id=rows[0].id, recording_consent=True, transcript=TRANSCRIPT)
        nocons = CallLog(call_ref=f"CALL2-{s}", phone_number="+254700000002", agent_id=rows[0].id, recording_consent=False, transcript="x")
        bot = CRMChatSession(token_hash=uuid4().hex, status="BOT", created_at=datetime.now(timezone.utc), last_message_at=datetime.now(timezone.utc))
        human = CRMChatSession(token_hash=uuid4().hex, status="CLOSED", created_at=datetime.now(timezone.utc), last_message_at=datetime.now(timezone.utc))
        db.add_all([call, nocons, bot, human])
        await db.flush()
        now = datetime.now(timezone.utc)
        db.add_all([CRMChatMessage(session_id=bot.id, sender="VISITOR", body="hi", created_at=now),
                    CRMChatMessage(session_id=human.id, sender="VISITOR", body="Your POVU detergent leaked in the carton.", created_at=now),
                    CRMChatMessage(session_id=human.id, sender="AGENT", body="Sorry, we will replace it tomorrow.", created_at=now)])
        await db.commit()
        ann, ben, mgr = _user(rows[0].id), _user(rows[1].id), _user(rows[2].id, "crm.view_all", "crm.edit_all")
        cid, ncid, bid, hid = call.id, nocons.id, bot.id, human.id

        monkeypatch.setattr(settings, "CONVERSATION_INTELLIGENCE_ENABLED", False)
        with pytest.raises(HTTPException) as e:                                   # opt-in
            await api.analyse("call", cid, db, ann)
        assert e.value.status_code == 409
        monkeypatch.setattr(settings, "CONVERSATION_INTELLIGENCE_ENABLED", True)
        with pytest.raises(HTTPException) as e:                                   # no consent → never analysed
            await api.analyse("call", ncid, db, ann)
        assert e.value.status_code == 422
        with pytest.raises(HTTPException) as e:                                   # someone else's call
            await api.analyse("call", cid, db, ben)
        assert e.value.status_code == 404

        out = await api.analyse("call", cid, db, ann)
        kinds = {f["kind"] for f in out["findings"]}
        assert {"objection", "question", "next_step", "theme"} <= kinds
        labels = {f["label"] for f in out["findings"] if f["kind"] == "objection"}
        assert {"price", "delivery"} <= labels
        for f in out["findings"]:                                                 # every quote is verbatim, offset correct
            assert TRANSCRIPT[f["offset"]:f["offset"] + len(f["quote"])] == f["quote"]
        assert set(out["counts"]) == set(ci.KINDS) and "score" not in out and out["status"] == "PENDING_REVIEW"

        # AI suggestions that do not quote the text are dropped
        assert ci.verified(TRANSCRIPT, [{"kind": "objection", "label": "price", "quote": "price is too expensive"},
                                        {"kind": "objection", "label": "made up", "quote": "they hate the product"},
                                        {"kind": "sentiment", "quote": "Good morning"}]) == [
            {"kind": "objection", "label": "price", "quote": "price is too expensive", "offset": TRANSCRIPT.find("price is too expensive")}]

        # chats: bot-only refused; a staff-handled chat is analysed by a manager only
        with pytest.raises(HTTPException):
            await api.analyse("chat", hid, db, ann)
        with pytest.raises(HTTPException) as e:
            await api.analyse("chat", bid, db, mgr)
        assert e.value.status_code == 422
        chat_out = await api.analyse("chat", hid, db, mgr)
        assert any(f["label"] == "quality" for f in chat_out["findings"])

        # visibility: Ann sees her own only; the manager sees both
        assert [i["source_id"] for i in (await api.list_insights(None, 100, db, ann))["items"]] == [str(cid)]
        lst = await api.list_insights(None, 100, db, mgr)
        assert len(lst["items"]) == 2 and lst["objections_by_type"]["price"] >= 1

        # review: only managers, never their own conversation
        iid = __import__("uuid").UUID(out["id"])
        with pytest.raises(HTTPException) as e:
            await api.review(iid, api.ReviewIn(status="REVIEWED"), db, ann)
        assert e.value.status_code == 403
        done = await api.review(iid, api.ReviewIn(status="REVIEWED", coaching_note="Offer the 12-carton price tier when price comes up."), db, mgr)
        assert done["status"] == "REVIEWED" and done["coaching_note"].startswith("Offer")
        self_mgr = _user(rows[0].id, "crm.edit_all")
        with pytest.raises(HTTPException) as e:
            await api.review(iid, api.ReviewIn(status="REJECTED"), db, self_mgr)
        assert e.value.status_code == 409
