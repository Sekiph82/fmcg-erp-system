"""M36.S04.T002 telephony on disposable PostgreSQL: own-call scoping, recording only with consent and
within retention, transcripts behind a company switch, failed calls flagged for follow-up, and
click-to-call without a telephony provider (tel: link + DIALED log)."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select

from app.api.v1.endpoints import voip
from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from app.models.voip import CallLog

TASK_DB_ENV = "M36_S04_T002_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S04_T002_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s04_t002_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(uid, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, is_superuser=False, access_scopes=[], company_id=None,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


async def _list(db, user, **kw):
    return await voip.list_calls(customer_id=None, agent_id=None, direction=None, outcome=None, limit=500,
                                 db=db, current_user=user, **kw)


@pytest.mark.asyncio
async def test_telephony_consent_retention_scope_click_to_call(monkeypatch):
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        rows = [User(email=f"{n}-{s}@povu.example", username=f"{n}{s}", full_name=n, hashed_password="x") for n in ("ann", "ben", "mgr")]
        db.add_all(rows)
        await db.commit()
        ann, ben = _user(rows[0].id, "crm.view"), _user(rows[1].id, "crm.view")
        mgr = _user(rows[2].id, "crm.view_all")

        # input validation at the boundary
        with pytest.raises(ValidationError):
            voip.CallIn(phone_number="call me maybe")
        with pytest.raises(ValidationError):
            voip.CallIn(phone_number="+254700000001", recording_url="http://insecure.example/r.mp3")
        with pytest.raises(ValidationError):
            voip.CallIn(phone_number="+254700000001", outcome="WHATEVER")

        # a recording without consent is refused; with consent it is kept until the retention date
        with pytest.raises(HTTPException) as e:
            await voip.create_call_log(voip.CallIn(phone_number="+254700000001", recording_url="https://rec.example/a.mp3"), db, ann)
        assert e.value.status_code == 422
        await db.rollback()
        ok = await voip.create_call_log(voip.CallIn(phone_number="+254700000001", recording_consent=True, consent_note="agreed at call start",
                                                    recording_url="https://rec.example/a.mp3", duration_seconds=95), db, ann)
        call = await db.get(CallLog, UUID(ok["id"]))
        days = (call.recording_expires_at - datetime.now(timezone.utc)).days
        assert settings.CALL_RECORDING_RETENTION_DAYS - 1 <= days <= settings.CALL_RECORDING_RETENTION_DAYS

        # failed outcomes are flagged for follow-up automatically
        busy = await voip.create_call_log(voip.CallIn(phone_number="+254700000002", outcome="BUSY"), db, ann)
        assert (await db.get(CallLog, UUID(busy["id"]))).follow_up_required is True

        # click-to-call without a provider: tel: link + DIALED log owned by the caller
        dialed = await voip.click_to_call(voip.CallIn(phone_number="+254 700 000 003"), db, ben)
        assert dialed["dial"] == "tel:+254700000003" and dialed["provider"] is None
        assert (await db.get(CallLog, UUID(dialed["id"]))).outcome == "DIALED"

        # scoping: own calls only, managers with view_all see everything; stats follow the same scope
        mine = {r["id"] for r in await _list(db, ann)}
        assert ok["id"] in mine and busy["id"] in mine and dialed["id"] not in mine
        everyone = {r["id"] for r in await _list(db, mgr)}
        assert {ok["id"], busy["id"], dialed["id"]} <= everyone
        assert (await voip.call_stats(db, ben))["total_calls"] == 1
        assert (await voip.call_stats(db, mgr))["total_calls"] >= 3
        row = next(r for r in await _list(db, ann) if r["id"] == ok["id"])
        assert row["recording_url"] == "https://rec.example/a.mp3" and row["recording_consent"] is True

        # someone else's call: invisible (404) to a plain user, visible but read-only (403) to view_all
        with pytest.raises(HTTPException) as e:
            await voip.update_call_log(UUID(ok["id"]), voip.CallPatch(notes="mine now"), db, ben)
        assert e.value.status_code == 404
        with pytest.raises(HTTPException) as e:
            await voip.update_call_log(UUID(ok["id"]), voip.CallPatch(notes="manager edit"), db, mgr)
        assert e.value.status_code == 403
        await db.rollback()
        await voip.update_call_log(UUID(dialed["id"]), voip.CallPatch(outcome="FAILED"), db, ben)
        db.expire_all()
        assert (await db.get(CallLog, UUID(dialed["id"]))).follow_up_required is True   # PATCH flags failed calls too
        with pytest.raises(HTTPException) as e:                                          # unknown customer: 422, not 500
            await voip.click_to_call(voip.CallIn(phone_number="+254700000009", customer_id=uuid4()), db, ben)
        assert e.value.status_code == 422
        await db.rollback()
        # re-sending the same recording link never extends retention
        exp = (await db.get(CallLog, UUID(ok["id"]))).recording_expires_at
        await voip.update_call_log(UUID(ok["id"]), voip.CallPatch(recording_url="https://rec.example/a.mp3"), db, ann)
        db.expire_all()
        assert (await db.get(CallLog, UUID(ok["id"]))).recording_expires_at == exp

        # transcripts: off by default (409); on, they still need consent (422)
        with pytest.raises(HTTPException) as e:
            await voip.update_call_log(UUID(ok["id"]), voip.CallPatch(transcript="Hello"), db, ann)
        assert e.value.status_code == 409
        await db.rollback()
        monkeypatch.setattr(settings, "CALL_TRANSCRIPTION_ENABLED", True)
        with pytest.raises(HTTPException) as e:
            await voip.update_call_log(UUID(busy["id"]), voip.CallPatch(transcript="Hello"), db, ann)
        assert e.value.status_code == 422
        await db.rollback()
        await voip.update_call_log(UUID(ok["id"]), voip.CallPatch(transcript="Hello, about POVU deliveries"), db, ann)
        db.expire_all()
        assert (await db.get(CallLog, UUID(ok["id"]))).transcript

        # withdrawn consent removes the recording and transcript
        await voip.update_call_log(UUID(ok["id"]), voip.CallPatch(recording_consent=False), db, ann)
        db.expire_all()
        c = await db.get(CallLog, UUID(ok["id"]))
        assert c.recording_url is None and c.transcript is None and c.recording_consent is False

        # retention: an expired recording is hidden at once and purged by the daily job; the call stays
        again = await voip.create_call_log(voip.CallIn(phone_number="+254700000004", recording_consent=True,
                                                       recording_url="https://rec.example/b.mp3"), db, ann)
        c = await db.get(CallLog, UUID(again["id"]))
        c.recording_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db.commit()
        row = next(r for r in await _list(db, ann) if r["id"] == again["id"])
        assert row["recording_url"] is None
        with pytest.raises(HTTPException) as e:                       # no transcript for an expired recording
            await voip.update_call_log(UUID(again["id"]), voip.CallPatch(transcript="late"), db, ann)
        assert e.value.status_code == 422
        await db.rollback()
        legacy_id = uuid4()
        legacy = CallLog(id=legacy_id, call_ref=f"CALL-L{s}", phone_number="+254700000005", agent_id=ann.id,
                         recording_url="https://rec.example/old.mp3")       # pre-consent era row
        db.add(legacy)
        await db.commit()
        assert await voip.purge_expired_recordings(db) >= 2
        await db.commit()
        db.expire_all()
        assert (await db.get(CallLog, legacy_id)).recording_url is None
        await db.commit()
        db.expire_all()
        c = await db.get(CallLog, UUID(again["id"]))
        assert c is not None and c.recording_url is None and c.recording_expires_at is None
