"""M36.S03.T005 website live chat on disposable PostgreSQL: token-protected visitor chat, help-article bot,
hand-off to staff via the CRM inbox, consent-based lead creation, spam/rate controls and retention purge."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select
from starlette.requests import Request

from app.api.v1.endpoints import chat_public as public
from app.api.v1.endpoints import crm_pipeline as staff
from app.db.session import AsyncSessionLocal, engine
from app.models.crm import CRMChatSession, CRMContactConsent, CRMConversation, CRMRecord
from app.models.knowledge_base import KBArticle
from app.models.user import User
from app.services import crm_chat_service as chat
from app.services import crm_inbox_service as inbox

TASK_DB_ENV = "M36_S03_T005_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S03_T005_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s03_t005_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _req(ip: str) -> Request:
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": (ip, 5000)})


def _user(uid, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, is_superuser=False, access_scopes=[], company_id=None,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_live_chat_bot_handoff_lead_limits_purge():
    s = uuid4().hex[:8]
    ip = f"41.90.{int(s[:2], 16)}.{int(s[2:4], 16)}"
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        agent_row = User(email=f"ag-{s}@povu.example", username=f"ag{s}", full_name="Agent", hashed_password="x")
        db.add_all([agent_row,
                    KBArticle(slug=f"deliveries-{s}", title=f"Deliveries{s} and delivery days", summary="When we deliver to shops",
                              content_md="Mon-Sat", status="PUBLISHED", is_internal_only=False),
                    KBArticle(slug=f"secret-{s}", title=f"Deliveries{s} internal margins", content_md="x", status="PUBLISHED",
                              is_internal_only=True)])
        await db.commit()
        agent = _user(agent_row.id, "crm.view_all", "crm.edit_all")

        # honeypot and no-consent: no lead
        with pytest.raises(HTTPException) as e:
            await public.start_chat(public.StartIn(website="http://spam.example"), _req(ip), db)
        assert e.value.status_code == 400
        anon = await public.start_chat(public.StartIn(name="Visitor"), _req(ip), db)
        assert anon["messages"][0]["from"] == "bot"
        assert (await db.get(CRMChatSession, UUID(anon["session_id"]))).crm_record_id is None

        # consent + e-mail: lead + consent recorded
        started = await public.start_chat(public.StartIn(name="Grace", email=f"grace-{s}@shops.example", consent=True,
                                                         page_url="https://povu.example/products"), _req(ip), db)
        sid, tok = UUID(started["session_id"]), started["token"]
        sess = await db.get(CRMChatSession, sid)
        lead = await db.get(CRMRecord, sess.crm_record_id)
        assert lead.contact_email == f"grace-{s}@shops.example" and lead.source_detail == "live chat"
        assert (await db.execute(select(CRMContactConsent.status).where(CRMContactConsent.email == f"grace-{s}@shops.example"))).scalar_one() == "SUBSCRIBED"
        with pytest.raises(HTTPException) as e:                       # someone else's token
            await public.poll(sid, None, "not-the-token-" + s, db)
        assert e.value.status_code == 404

        # bot answers from public help articles only (never internal ones)
        r = await public.say(sid, public.SayIn(body=f"Which deliveries{s} days do you have?"), tok, db)
        bot = r["messages"][-1]["body"]
        assert r["status"] == "BOT" and f"/kb/deliveries-{s}" in bot and "secret" not in bot
        # asking for a person hands off; the chat appears in the CRM inbox
        r = await public.say(sid, public.SayIn(body="I want to speak to a person about a big order"), tok, db)
        assert r["status"] == "WAITING"
        out = await inbox.list_conversations(db, agent, channel="CHAT")
        row = next(i for i in out["items"] if i["link"].endswith(str(sid)))
        assert row["unread"] and row["sla_due_at"] is not None
        assert not any(i["link"].endswith(anon["session_id"]) for i in out["items"])   # still with the bot: not in inbox

        # staff reply reaches the visitor; close ends it; the inbox follows
        with pytest.raises(HTTPException):                            # the route's guard: view-only users cannot reply
            await staff.require_any_permission(("crm.edit", "crm.edit_all"))(_user(agent_row.id, "crm.view"))
        await staff.chat_reply(str(sid), staff.ChatReplyIn(body="Hello Grace, how many cartons do you need?"), db, agent)
        seen = await public.poll(sid, None, tok, db)
        assert seen["messages"][-1] == {**seen["messages"][-1], "from": "agent", "body": "Hello Grace, how many cartons do you need?"}
        await staff.chat_close(str(sid), db, agent)
        with pytest.raises(HTTPException) as e:
            await public.say(sid, public.SayIn(body="one more thing"), tok, db)
        assert e.value.status_code == 409
        await db.rollback()
        conv = (await db.execute(select(CRMConversation).where(CRMConversation.source_ref == str(sid))
                                 .execution_options(populate_existing=True))).scalar_one()
        await inbox.sync(db)
        await db.commit()
        await db.refresh(conv)
        assert conv.status == "CLOSED"

        # spam limits: new chats per connection, messages per minute
        for _ in range(chat.NEW_CHATS_PER_HOUR - 2):                  # 2 already started from this address
            await public.start_chat(public.StartIn(), _req(ip), db)
        with pytest.raises(HTTPException) as e:
            await public.start_chat(public.StartIn(), _req(ip), db)
        assert e.value.status_code == 429
        await db.rollback()
        flood = await public.start_chat(public.StartIn(), _req(f"102.1.{int(s[4:6], 16)}.9"), db)
        fid, ftok = UUID(flood["session_id"]), flood["token"]
        with pytest.raises(HTTPException) as e:
            for _ in range(chat.MESSAGES_PER_MINUTE + 1):
                await public.say(fid, public.SayIn(body="buy buy"), ftok, db)
        assert e.value.status_code == 429
        await db.rollback()

        # retention: closed chats older than the period are deleted with their messages
        old = await db.get(CRMChatSession, sid)
        old.last_message_at = old.closed_at = datetime.now(timezone.utc) - timedelta(days=chat.RETENTION_DAYS + 1)
        await db.commit()
        assert await chat.purge_old(db) >= 1
        await db.commit()
        assert await db.get(CRMChatSession, sid) is None
        # silent bot-only chats go after a week; long chats are capped; the newest messages are returned
        idle = await db.get(CRMChatSession, UUID(anon["session_id"]))       # never got past the bot
        idle.last_message_at = datetime.now(timezone.utc) - timedelta(days=chat.BOT_IDLE_DAYS + 1)
        await db.commit()
        await chat.purge_old(db)
        await db.commit()
        assert await db.get(CRMChatSession, UUID(anon["session_id"])) is None
        assert await db.get(CRMChatSession, fid) is not None              # handed off and recent: kept
