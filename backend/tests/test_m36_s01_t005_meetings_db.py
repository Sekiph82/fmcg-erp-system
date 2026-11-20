"""M36.S01.T005 meeting scheduling on disposable PostgreSQL: DST-safe times, double-booking protection,
stale-update conflicts, cancellations with calendar CANCEL, e-mailed invites (fake SMTP), free slots on a
DST day, visibility, and a revocable personal calendar feed."""
from __future__ import annotations

import os
import re
from datetime import date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints import meetings as api
from app.api.v1.endpoints import meetings_public as public
from app.db.session import AsyncSessionLocal, engine
from app.models.email_integration import EmailAccount, EmailProvider
from app.models.meetings import MeetingRecord
from app.models.user import User
from app.services import email_mailbox_service as mbx
from app.services import meeting_service as svc

TASK_DB_ENV = "M36_S01_T005_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S01_T005_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s01_t005_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(row, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=row.id, email=row.email, full_name=row.full_name, is_superuser=False, access_scopes=[],
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


def test_time_zone_conversion_is_dst_safe():
    # London: clocks go forward 29 Mar 2026 01:00 -> 02:00, back 25 Oct 2026 02:00 -> 01:00
    assert svc.to_utc(datetime(2026, 3, 28, 10, 0), "Europe/London") == datetime(2026, 3, 28, 10, 0)   # GMT
    assert svc.to_utc(datetime(2026, 3, 30, 10, 0), "Europe/London") == datetime(2026, 3, 30, 9, 0)    # BST
    with pytest.raises(svc.MeetingError, match="does not exist"):
        svc.to_utc(datetime(2026, 3, 29, 1, 30), "Europe/London")                                       # gap
    assert svc.to_utc(datetime(2026, 10, 25, 1, 30), "Europe/London") == datetime(2026, 10, 25, 0, 30)  # fold=0
    assert svc.to_utc(datetime(2026, 11, 23, 10, 0), "Africa/Nairobi") == datetime(2026, 11, 23, 7, 0)
    with pytest.raises(svc.MeetingError):
        svc.zone("Mars/Olympus")
    ics = svc.calendar([svc.vevent(SimpleNamespace(id="x", sequence=2, scheduled_at=datetime(2026, 11, 23, 7), duration_minutes=30,
                                                   title="Order review, POVU; 1 L", status="SCHEDULED", agenda="a" * 200,
                                                   meeting_url=None, attendees=[]), None)], method="REQUEST")
    assert "SEQUENCE:2" in ics and "DTSTART:20261123T070000Z" in ics and "SUMMARY:Order review\\, POVU\\; 1 L" in ics
    assert all(len(line.encode()) <= 75 for line in ics.split("\r\n"))                                  # RFC 5545 folding


@pytest.mark.asyncio
async def test_booking_conflicts_invites_cancel_feed(monkeypatch):
    s = uuid4().hex[:8]
    sent = []
    monkeypatch.setattr(mbx, "smtp_send", lambda host, port, user, password, mime: sent.append(mime))
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        host_row = User(email=f"host-{s}@povu.example", username=f"mh{s}", full_name="Rep Amina", hashed_password="x")
        guest_row = User(email=f"guest-{s}@povu.example", username=f"mg{s}", full_name="Guest", hashed_password="x")
        other_row = User(email=f"other-{s}@povu.example", username=f"mo{s}", full_name="Other", hashed_password="x")
        db.add_all([host_row, guest_row, other_row])
        await db.flush()
        db.add(EmailAccount(provider=EmailProvider.GMAIL, email_address=host_row.email, created_by_id=host_row.id,
                            imap_host="imap.gmail.com", imap_port=993, smtp_host="smtp.gmail.com", smtp_port=465,
                            username=host_row.email, secret_enc=mbx.encrypt("pw")))
        await db.commit()
        host, guest, other = _user(host_row), _user(guest_row), _user(other_row)

        body = api.MeetingIn(title="POVU AllClean listing review", start=datetime(2026, 11, 23, 10, 0), time_zone="Africa/Nairobi",
                             duration_minutes=60, attendees=[{"name": "Mama Duka", "email": f"duka-{s}@shops.example"},
                                                             {"email": guest_row.email}])
        r = await api.create_meeting(body, db, host)
        assert r["scheduled_at"] == "2026-11-23T07:00:00+00:00" and r["meeting_url"].startswith("https://meet.jit.si/POVU-")
        assert r["invites"] == "SENT"
        invite = sent[-1]
        cal = next(p for p in invite.iter_attachments() if p.get_content_type() == "text/calendar")
        assert cal.get_param("method") == "REQUEST" and "SEQUENCE:0" in cal.get_content()
        mid = uuid4().hex and r["id"]

        # double booking: overlapping slot refused, back-to-back allowed
        for start in (datetime(2026, 11, 23, 10, 30), datetime(2026, 11, 23, 9, 30)):
            with pytest.raises(HTTPException) as e:
                await api.create_meeting(api.MeetingIn(title="Clash", start=start, duration_minutes=60, send_invites=False), db, host)
            assert e.value.status_code == 409
            await db.rollback()
        nxt = await api.create_meeting(api.MeetingIn(title="Next", start=datetime(2026, 11, 23, 11, 0), duration_minutes=30,
                                                     send_invites=False), db, host)
        # the same wall time in London is a different instant: no clash
        await api.create_meeting(api.MeetingIn(title="London call", start=datetime(2026, 11, 23, 13, 0), time_zone="Europe/London",
                                               duration_minutes=30, send_invites=False), db, host)
        with pytest.raises(HTTPException) as e:  # a non-existent local time is refused
            await api.create_meeting(api.MeetingIn(title="Gap", start=datetime(2026, 3, 29, 1, 30), time_zone="Europe/London"), db, host)
        assert e.value.status_code == 422

        # free slots: the booked hours are not offered
        slots = (await api.availability(date(2026, 11, 23), "Africa/Nairobi", 60, db, host))["slots"]
        local = {x["start_local"][11:16] for x in slots}
        assert "10:00" not in local and "10:30" not in local and "11:00" not in local and "08:00" in local and "11:30" in local
        dst = await svc.free_slots(db, host.id, date(2026, 3, 29), "Europe/London", 60)
        assert dst[0]["start_local"].startswith("2026-03-29T08:00:00+01:00")                              # BST already

        # moving a meeting onto another: 409; a stale edit: 409; a real change bumps SEQUENCE and re-invites
        from uuid import UUID
        with pytest.raises(HTTPException) as e:
            await api.update_meeting(UUID(nxt["id"]), api.MeetingPatch(start=datetime(2026, 11, 23, 10, 15)), db, host)
        assert e.value.status_code == 409
        await db.rollback()
        with pytest.raises(HTTPException) as e:
            await api.update_meeting(UUID(mid), api.MeetingPatch(title="x", expected_sequence=5), db, host)
        assert e.value.status_code == 409
        await db.rollback()
        upd = await api.update_meeting(UUID(mid), api.MeetingPatch(start=datetime(2026, 11, 23, 14, 0), expected_sequence=0), db, host)
        assert upd["sequence"] == 1 and upd["invites"] == "SENT"
        assert "SEQUENCE:1" in next(p for p in sent[-1].iter_attachments() if p.get_content_type() == "text/calendar").get_content()

        # visibility: invited guest sees it, others do not and cannot change or cancel it
        assert any(m["id"] == mid for m in await api.list_meetings(None, None, None, 100, db, guest))
        assert not any(m["id"] == mid for m in await api.list_meetings(None, None, None, 100, db, other))
        with pytest.raises(HTTPException) as e:
            await api.cancel_meeting(UUID(mid), True, db, other)
        assert e.value.status_code == 404
        with pytest.raises(HTTPException) as e:
            await api.update_meeting(UUID(mid), api.MeetingPatch(title="hijack"), db, guest)
        assert e.value.status_code == 403
        await db.rollback()

        # personal feed: works, rotation kills the old link, revoke kills all
        url1 = (await api.rotate_calendar_feed(db, host))["url"]
        tok1 = url1.rsplit("/", 1)[1][:-4]
        feed = (await public.calendar_feed(tok1, db)).body.decode()
        assert f"UID:{mid}@povu-erp" in feed and "X-WR-CALNAME" in feed
        guest_tok = (await api.rotate_calendar_feed(db, guest))["url"].rsplit("/", 1)[1][:-4]
        assert f"UID:{mid}@povu-erp" in (await public.calendar_feed(guest_tok, db)).body.decode()
        tok2 = (await api.rotate_calendar_feed(db, host))["url"].rsplit("/", 1)[1][:-4]
        with pytest.raises(HTTPException):
            await public.calendar_feed(tok1, db)
        await public.calendar_feed(tok2, db)
        await api.revoke_calendar_feed(db, host)
        with pytest.raises(HTTPException):
            await public.calendar_feed(tok2, db)

        # cancel: kept as history, calendar CANCEL with a higher SEQUENCE, the slot is free again
        c = await api.cancel_meeting(UUID(mid), True, db, host)
        assert c["invites"] == "SENT"
        cancel = next(p for p in sent[-1].iter_attachments() if p.get_content_type() == "text/calendar")
        assert cancel.get_param("method") == "CANCEL" and "STATUS:CANCELLED" in cancel.get_content() and "SEQUENCE:2" in cancel.get_content()
        assert (await db.get(MeetingRecord, UUID(mid))).status == "CANCELLED"
        await api.create_meeting(api.MeetingIn(title="Rebooked", start=datetime(2026, 11, 23, 14, 0), send_invites=False), db, host)

        # no connected mailbox: the meeting is saved, the host is told the invite did not go out
        r = await api.create_meeting(api.MeetingIn(title="Guest's own", start=datetime(2026, 11, 24, 9, 0),
                                                   attendees=[{"email": f"duka-{s}@shops.example"}]), db, guest)
        assert r["invites"] == "NO_MAILBOX"


@pytest.mark.asyncio
async def test_review_fixes_matching_injection_removed_reopen(monkeypatch):
    from uuid import UUID
    s = uuid4().hex[:8]
    sent = []
    monkeypatch.setattr(mbx, "smtp_send", lambda host, port, user, password, mime: sent.append(mime))
    async with AsyncSessionLocal() as db:
        host_row = User(email=f"h2-{s}@povu.example", username=f"h2{s}", full_name="Host", hashed_password="x")
        john_row = User(email=f"john-{s}@povu.example", username=f"jo{s}", full_name="John", hashed_password="x")
        wild_row = User(email=f"j_hn-{s}@povu.example", username=f"jw{s}", full_name="Wild", hashed_password="x")
        admin_row = User(email=f"ad-{s}@povu.example", username=f"ad{s}", full_name="Admin", hashed_password="x")
        db.add_all([host_row, john_row, wild_row, admin_row])
        await db.flush()
        db.add(EmailAccount(provider=EmailProvider.GMAIL, email_address=host_row.email, created_by_id=host_row.id,
                            imap_host="imap.gmail.com", imap_port=993, smtp_host="smtp.gmail.com", smtp_port=465,
                            username=host_row.email, secret_enc=mbx.encrypt("pw")))
        await db.commit()
        host, john, wild, admin = _user(host_row), _user(john_row), _user(wild_row), _user(admin_row, "crm.edit_all")

        r = await api.create_meeting(api.MeetingIn(
            title="Shelf plan", start=datetime(2026, 12, 1, 9, 0),
            attendees=[{"email": f"JOHN-{s}@povu.example", "name": 'Bob:mailto:evil@x.example"'},
                       {"email": f"drop-{s}@shops.example"}]), db, host)
        mid = UUID(r["id"])
        ics = next(p for p in sent[-1].iter_attachments() if p.get_content_type() == "text/calendar").get_content()
        assert f'ATTENDEE;CN="Bob:mailto:evil@x.example";RSVP=TRUE:mailto:john-{s}@povu.example' in ics.replace("\r\n ", "")

        # exact, case-insensitive invitee match: John sees it, j_hn (LIKE wildcard) does not
        mine = {m["id"]: m for m in await api.list_meetings(None, None, None, 100, db, john)}
        assert str(mid) in mine and mine[str(mid)]["can_change"] is False
        assert str(mid) not in {m["id"] for m in await api.list_meetings(None, None, None, 100, db, wild)}

        # an editor who is not the host: invites still come from the host; removed invitee gets a CANCEL
        n = len(sent)
        await api.update_meeting(mid, api.MeetingPatch(attendees=[{"email": f"john-{s}@povu.example"}]), db, admin)
        assert all(host_row.email in str(m["From"]) for m in sent[n:]) and len(sent) - n == 2
        cancel = next(p for p in sent[-1].iter_attachments() if p.get_content_type() == "text/calendar")
        assert cancel.get_param("method") == "CANCEL" and str(sent[-1]["To"]) == f"drop-{s}@shops.example"

        # empty required field: 422, not a database error
        with pytest.raises(HTTPException) as e:
            await api.update_meeting(mid, api.MeetingPatch.model_validate({"title": None}), db, host)
        assert e.value.status_code == 422
        await db.rollback()

        # re-opening a completed meeting onto a now-booked slot: 409
        await api.update_meeting(mid, api.MeetingPatch(status="COMPLETED"), db, host)
        await api.create_meeting(api.MeetingIn(title="Took the slot", start=datetime(2026, 12, 1, 9, 30), send_invites=False), db, host)
        with pytest.raises(HTTPException) as e:
            await api.update_meeting(mid, api.MeetingPatch(status="SCHEDULED"), db, host)
        assert e.value.status_code == 409
