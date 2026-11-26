"""M49.S01.T001 recurring Google / Outlook meetings against the local simulators (disposable PostgreSQL, M49_DB=1).

Covers: RRULE subset + DST (spring-forward gap, fall-back overlap, wall time kept across the change), Graph pattern
mapping, create -> one provider master + one invitation, edit this / following / all, cancel this / following / all,
exception sync to the provider instance, provider-side move / cancel mapped back, double-booking refusal, RSVP, REPLY
mail parsing, free/busy, legacy per-meeting endpoints refusing series occurrences, and access control.
"""
from __future__ import annotations

import base64
from datetime import datetime
from email import message_from_bytes, policy
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core import provider_http
from app.services import calendar_series_service as svc
from m49_calmail_helpers import SIM, env, new_user, requires_db, _tables_and_dispose  # noqa: F401

START = datetime(2027, 3, 8, 9, 0)           # a Monday; New York changes to summer time on Sunday 2027-03-14


# ── pure rule / DST checks (no database) ─────────────────────────────────────

def test_rule_validation_and_defaults():
    start = datetime(2027, 3, 8, 9)
    assert svc.normalize_rrule("RRULE:FREQ=WEEKLY;COUNT=4", start) == "FREQ=WEEKLY;BYDAY=MO;COUNT=4"
    assert svc.normalize_rrule("FREQ=MONTHLY", start) == "FREQ=MONTHLY;BYMONTHDAY=8"
    assert svc.normalize_rrule("FREQ=MONTHLY;BYDAY=2TU", start) == "FREQ=MONTHLY;BYDAY=2TU"
    assert svc.normalize_rrule("FREQ=WEEKLY;UNTIL=20271231", start).endswith("UNTIL=20271231T235959")
    for bad in ("FREQ=SECONDLY", "FREQ=DAILY;BYDAY=MO", "FREQ=WEEKLY;COUNT=2;UNTIL=20271231", "FREQ=WEEKLY;BYSETPOS=1",
                "FREQ=MONTHLY;BYDAY=MO", "FREQ=WEEKLY;UNTIL=20200101", "FREQ=WEEKLY;COUNT=9999", "FREQ=WEEKLY;UNTIL=20271231T000000Z"):
        with pytest.raises(svc.SeriesError):
            svc.normalize_rrule(bad, start)


def test_dst_wall_time_is_kept_and_gaps_and_overlaps_are_handled():
    horizon = datetime(2028, 1, 1)
    s = svc.slots("FREQ=WEEKLY;BYDAY=MO;COUNT=4", START, "America/New_York", horizon)
    utc = [svc._utc(d, "America/New_York").strftime("%m-%d %H:%M") for d in s]
    assert utc == ["03-08 14:00", "03-15 13:00", "03-22 13:00", "03-29 13:00"]      # 09:00 local every time
    gap = svc.slots("FREQ=DAILY;COUNT=3", datetime(2027, 3, 13, 2, 30), "America/New_York", horizon)
    assert [svc._utc(d, "America/New_York").strftime("%m-%d %H:%M") for d in gap] == ["03-13 07:30", "03-14 07:30", "03-15 06:30"]
    # 02:30 does not exist on 03-14: it runs after the gap (03:30 EDT = 07:30 UTC); other days are 02:30 local
    ov = svc.slots("FREQ=DAILY;COUNT=2", datetime(2027, 11, 6, 1, 30), "America/New_York", horizon)
    assert [svc._utc(d, "America/New_York").strftime("%m-%d %H:%M") for d in ov] == ["11-06 05:30", "11-07 05:30"]  # first 01:30
    lon = svc.slots("FREQ=WEEKLY;BYDAY=SU;COUNT=2", datetime(2027, 3, 21, 9), "Europe/London", horizon)
    assert [svc._utc(d, "Europe/London").strftime("%m-%d %H:%M") for d in lon] == ["03-21 09:00", "03-28 08:00"]


def test_graph_pattern_and_google_rule_mapping():
    s = SimpleNamespace(rrule="FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,WE;UNTIL=20271231T235959", time_zone="Europe/London",
                        start_local=datetime(2027, 3, 8, 9))
    g = svc.graph_recurrence(s)
    assert g["pattern"] == {"interval": 2, "type": "weekly", "daysOfWeek": ["monday", "wednesday"], "firstDayOfWeek": "monday"}
    assert g["range"] == {"startDate": "2027-03-08", "recurrenceTimeZone": "Europe/London", "type": "endDate", "endDate": "2027-12-31"}
    assert svc.provider_rrule(s).endswith("UNTIL=20271231T235959Z")               # London in winter = UTC
    s.rrule = "FREQ=MONTHLY;BYDAY=-1FR;COUNT=3"
    assert svc.graph_recurrence(s)["pattern"]["index"] == "last"
    s.rrule = "FREQ=YEARLY;BYMONTH=3;BYMONTHDAY=8"
    assert svc.graph_recurrence(s)["pattern"] == {"interval": 1, "type": "absoluteYearly", "month": 3, "dayOfMonth": 8}
    assert svc.graph_recurrence(s)["range"]["type"] == "noEnd"


def test_reply_parser_reads_partstat_and_recurrence_id():
    sid = "6f0c7a1e-2f55-4f3e-8f0e-1d2c3b4a5e6f"
    ics = ("BEGIN:VCALENDAR\r\nMETHOD:REPLY\r\nBEGIN:VEVENT\r\nUID:" + sid + "@povu-erp-series\r\n"
           "RECURRENCE-ID;TZID=America/New_York:20270315T090000\r\nATTENDEE;PARTSTAT=DECLINED:mailto:Buyer@example.com\r\n"
           "END:VEVENT\r\nEND:VCALENDAR\r\n")
    assert svc.parse_reply(ics) == {"series_id": sid, "email": "buyer@example.com", "response": "declined", "occ_date": "2027-03-15"}
    assert svc.parse_reply(ics.replace("METHOD:REPLY", "METHOD:REQUEST")) is None


# ── database + simulators ────────────────────────────────────────────────────

@pytest.fixture(params=["google", "microsoft"])
async def ctx(request, env, monkeypatch):
    from app.db.session import AsyncSessionLocal
    provider = request.param
    if provider == "google":
        env.use_main_gmail(monkeypatch)
    async with AsyncSessionLocal() as db:
        host = await new_user(db, "host")
        cal = await env.connect(db, host, provider, "calendar", host.email)
        await env.connect(db, host, provider, "mail", host.email)
        yield SimpleNamespace(env=env, db=db, host=host, provider=provider, cal=cal, api=env.api(host),
                              tz="America/New_York" if provider == "microsoft" else "Europe/London")


async def _mails(c):
    """Calendar parts of every mail the host's mailbox sent."""
    async with provider_http.provider_client() as p:
        if c.provider == "google":
            raws = [base64.b64decode(x) for x in (await p.get(f"{SIM}/_control/sent/google")).json()["sent"]]
        else:
            raws = [base64.b64decode(x["raw_b64"]) for x in (await p.get(f"{SIM}/cm/_control/sent")).json()]
    out = []
    for raw in raws:
        for part in message_from_bytes(raw, policy=policy.default).walk():
            if part.get_content_type() == "text/calendar":
                out.append(part.get_content())
    return out


async def _create(c, **over):
    body = {"title": "POVU AllClean 1 L range review", "start": START.isoformat(), "time_zone": c.tz,
            "rrule": "FREQ=WEEKLY;BYDAY=MO;COUNT=8", "duration_minutes": 60,
            "attendees": [{"email": "buyer@example.com", "name": "Synthetic Buyer"}], **over}
    r = await c.api.post("/api/v1/meeting-series", json=body)
    return r


async def _detail(c, sid):
    return (await c.api.get(f"/api/v1/meeting-series/{sid}")).json()


async def _provider(c):
    return await c.env.cm_get(f"/_control/events/{c.provider}")


@requires_db
async def test_create_keeps_wall_time_across_dst_and_sends_one_invitation(ctx):
    r = await _create(ctx)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["occurrences"] == 8 and body["invites"] == "SENT" and body["calendar"] == "SYNCED"
    d = await _detail(ctx, body["id"])
    hours = {o["date"]: o["start"][11:16] for o in d["occurrences"]}
    if ctx.provider == "microsoft":                                  # New York: 09:00 local = 14:00Z, then 13:00Z after 03-14
        assert hours["2027-03-08"] == "14:00" and hours["2027-03-15"] == "13:00" and hours["2027-04-26"] == "13:00"
    else:                                                            # London changes on 03-28
        assert hours["2027-03-22"] == "09:00" and hours["2027-03-29"] == "08:00"
    assert all(o["local_start"][11:16] == "09:00" for o in d["occurrences"])
    ics = await _mails(ctx)
    assert len(ics) == 1                                             # one invitation for the whole series
    text = ics[0].replace("\r\n ", "")
    assert f"RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=8" in text and f"DTSTART;TZID={ctx.tz}:20270308T090000" in text
    assert text.count("BEGIN:VEVENT") == 1 and "METHOD:REQUEST" in text
    masters = [e for e in await _provider(ctx) if e["recur"]]
    assert len(masters) == 1                                         # one provider event, not eight
    # repeated push with the same sequence writes nothing new
    from app.services import calendar_sync_service as cal
    await cal.sync_connection(ctx.db, ctx.cal)
    await ctx.db.commit()
    assert len([e for e in await _provider(ctx) if e["recur"]]) == 1
    assert len(await _mails(ctx)) == 1


@requires_db
async def test_edit_scopes_exceptions_and_no_duplicate_invites(ctx):
    sid = (await _create(ctx)).json()["id"]
    # this occurrence: move 2027-03-15 one hour later -> exception, provider instance patched, one more mail
    r = await ctx.api.patch(f"/api/v1/meeting-series/{sid}", json={"scope": "this", "occurrence_date": "2027-03-15",
                                                                    "start": "2027-03-15T10:00:00", "title": "Moved review"})
    assert r.status_code == 200, r.text
    d = await _detail(ctx, sid)
    occ = {o["date"]: o for o in d["occurrences"]}
    assert occ["2027-03-15"]["is_exception"] and occ["2027-03-15"]["local_start"][11:16] == "10:00"
    assert occ["2027-03-15"]["title"] == "Moved review" and not occ["2027-03-22"]["is_exception"]
    ics = await _mails(ctx)
    assert len(ics) == 2 and ics[1].count("BEGIN:VEVENT") == 2 and "RECURRENCE-ID;TZID=" in ics[1]   # master + override
    prov = await _provider(ctx)
    inst = [e for e in prov if e["series"]]
    assert len(inst) == 1 and inst[0]["start_utc"][11:16] != "09:00"             # the exception instance carries the new time
    # cancel one occurrence -> EXDATE in the invite, provider instance cancelled
    r = await ctx.api.delete(f"/api/v1/meeting-series/{sid}", params={"scope": "this", "occurrence_date": "2027-03-22"})
    assert r.status_code == 200, r.text
    last = (await _mails(ctx))[-1].replace("\r\n ", "")
    assert "EXDATE;TZID=" in last and "20270322T090000" in last
    assert any(e["series"] and e["cancelled"] for e in await _provider(ctx))
    # all: new title reaches future non-exception occurrences only; the moved one keeps its own title
    r = await ctx.api.patch(f"/api/v1/meeting-series/{sid}", json={"scope": "all", "title": "Range review (all)"})
    assert r.status_code == 200, r.text
    d = await _detail(ctx, sid)
    occ = {o["date"]: o for o in d["occurrences"]}
    assert occ["2027-03-08"]["title"] == "Range review (all)" and occ["2027-03-29"]["title"] == "Range review (all)"
    assert occ["2027-03-15"]["title"] == "Moved review" and occ["2027-03-22"]["status"] == "CANCELLED"
    n_before = len(await _mails(ctx))
    # replaying the very same request body is a new change (sequence moves) but never sends two mails per change
    r = await ctx.api.patch(f"/api/v1/meeting-series/{sid}", json={"scope": "all", "title": "Range review (all)"})
    assert len(await _mails(ctx)) - n_before <= 1


@requires_db
async def test_this_and_following_splits_the_series_without_losing_or_doubling_dates(ctx):
    sid = (await _create(ctx)).json()["id"]
    r = await ctx.api.patch(f"/api/v1/meeting-series/{sid}", json={"scope": "following", "occurrence_date": "2027-03-29",
                                                                    "start": "2027-03-29T10:00:00", "duration_minutes": 45})
    assert r.status_code == 200, r.text
    ids = r.json()["series"]
    assert len(ids) == 2 and ids[0] == sid
    old, new = await _detail(ctx, ids[0]), await _detail(ctx, ids[1])
    assert old["rrule"] == "FREQ=WEEKLY;BYDAY=MO;COUNT=3"                    # 03-08, 03-15, 03-22 stay on the old series
    assert new["rrule"] == "FREQ=WEEKLY;BYDAY=MO;COUNT=5"
    assert [o["date"] for o in old["occurrences"]] == ["2027-03-08", "2027-03-15", "2027-03-22"]
    assert [o["date"] for o in new["occurrences"]] == ["2027-03-29", "2027-04-05", "2027-04-12", "2027-04-19", "2027-04-26"]
    assert {o["duration_minutes"] for o in new["occurrences"]} == {45} and new["occurrences"][0]["local_start"][11:16] == "10:00"
    assert {o["duration_minutes"] for o in old["occurrences"]} == {60}
    assert len([e for e in await _provider(ctx) if e["recur"] and not e["cancelled"]]) == 2
    # cancel this and following from 04-12 on the new series
    r = await ctx.api.delete(f"/api/v1/meeting-series/{ids[1]}", params={"scope": "following", "occurrence_date": "2027-04-12"})
    assert r.status_code == 200, r.text
    new = await _detail(ctx, ids[1])
    assert new["rrule"] == "FREQ=WEEKLY;BYDAY=MO;COUNT=2" and len(new["occurrences"]) == 2
    # cancel all of the old series: every future occurrence cancelled, a CANCEL mail, provider master removed
    r = await ctx.api.delete(f"/api/v1/meeting-series/{ids[0]}", params={"scope": "all"})
    assert r.status_code == 200
    old = await _detail(ctx, ids[0])
    assert old["status"] == "CANCELLED" and {o["status"] for o in old["occurrences"]} == {"CANCELLED"}
    assert "METHOD:CANCEL" in (await _mails(ctx))[-1]
    assert (await ctx.api.delete(f"/api/v1/meeting-series/{ids[0]}")).json()["invites"] == "ALREADY_CANCELLED"


@requires_db
async def test_double_booking_is_refused_for_create_and_for_moves(ctx):
    from app.models.meetings import MeetingRecord
    busy_at = svc._utc(datetime(2027, 3, 22, 9, 30), ctx.tz)                # 09:30 local on 03-22
    ctx.db.add(MeetingRecord(title="Existing distributor call", platform="jitsi", host_id=ctx.host.id, status="SCHEDULED",
                             scheduled_at=busy_at, duration_minutes=60, time_zone=ctx.tz, sequence=0, attendees=[]))
    await ctx.db.commit()
    r = await _create(ctx, start="2027-03-22T09:00:00", rrule="FREQ=DAILY;COUNT=3")      # first occurrence overlaps it
    assert r.status_code == 409 and r.json()["detail"]["conflicts"][0]["conflicts_with"] == "Existing distributor call"
    assert (await ctx.api.get("/api/v1/meeting-series")).json() == []                  # nothing was half-created
    sid = (await _create(ctx, start="2027-03-29T09:00:00", rrule="FREQ=WEEKLY;COUNT=3", title="Clean series")).json()["id"]
    # moving one occurrence onto the existing meeting is refused and changes nothing
    r = await ctx.api.patch(f"/api/v1/meeting-series/{sid}", json={"scope": "this", "occurrence_date": "2027-04-05",
                                                                    "start": "2027-03-22T09:30:00"})
    assert r.status_code == 409, r.text
    d = await _detail(ctx, sid)
    assert d["occurrences"][1]["local_start"][:10] == "2027-04-05" and not d["occurrences"][1]["is_exception"]
    # a whole-series time change that would land on a later meeting is refused, the series stays as it was
    ctx.db.add(MeetingRecord(title="Later call", platform="jitsi", host_id=ctx.host.id, status="SCHEDULED",
                             scheduled_at=svc._utc(datetime(2027, 4, 12, 10, 30), ctx.tz), duration_minutes=60,
                             time_zone=ctx.tz, sequence=0, attendees=[]))
    await ctx.db.commit()
    r = await ctx.api.patch(f"/api/v1/meeting-series/{sid}", json={"scope": "all", "start": "2027-03-29T10:00:00"})
    assert r.status_code == 409, r.text
    d = await _detail(ctx, sid)
    assert {o["local_start"][11:16] for o in d["occurrences"]} == {"09:00"}


@requires_db
async def test_provider_side_move_and_cancel_are_mapped_back(ctx):
    from app.services import calendar_sync_service as cal
    sid = (await _create(ctx)).json()["id"]
    d = await _detail(ctx, sid)
    first, second = d["occurrences"][1], d["occurrences"][2]          # 03-15 and 03-22
    moved_to = datetime.fromisoformat(first["start"]).replace(tzinfo=None) + (datetime(2027, 1, 1, 2) - datetime(2027, 1, 1))
    end = moved_to + (datetime(2027, 1, 1, 1) - datetime(2027, 1, 1))
    changes = [{"provider": ctx.provider, "master": next(e["id"] for e in await _provider(ctx) if e["recur"]),
                "orig": first["start"], "start": {"dateTime": moved_to.isoformat() + "+00:00", "timeZone": "UTC"},
                "end": {"dateTime": end.isoformat() + "+00:00", "timeZone": "UTC"}}]
    if ctx.provider == "google":                                       # Graph reports a removed instance by id only
        changes.append({"provider": "google", "master": changes[0]["master"], "orig": second["start"], "cancelled": True})
    await ctx.env.ctl({"instance_changes": changes})
    await cal.sync_connection(ctx.db, ctx.cal)
    await ctx.db.commit()
    d = await _detail(ctx, sid)
    occ = {o["date"]: o for o in d["occurrences"]}
    assert occ["2027-03-15"]["is_exception"] and occ["2027-03-15"]["start"][11:16] == f"{moved_to:%H:%M}"
    if ctx.provider == "google":
        assert occ["2027-03-22"]["status"] == "CANCELLED"
    # our own occurrences never became busy time that blocks the host's later edits
    r = await ctx.api.patch(f"/api/v1/meeting-series/{sid}", json={"scope": "this", "occurrence_date": "2027-03-29", "title": "Still editable"})
    assert r.status_code == 200, r.text


@requires_db
async def test_rsvp_reply_mail_free_busy_legacy_guard_and_access(ctx):
    sid = (await _create(ctx)).json()["id"]
    r = await ctx.api.post(f"/api/v1/meeting-series/{sid}/rsvp", json={"email": "buyer@example.com", "response": "declined",
                                                                       "occurrence_date": "2027-03-15"})
    assert r.status_code == 200 and r.json()["updated"] == 1
    r = await ctx.api.post(f"/api/v1/meeting-series/{sid}/rsvp", json={"email": "buyer@example.com", "response": "accepted"})
    assert r.json()["updated"] >= 6
    assert (await ctx.api.post(f"/api/v1/meeting-series/{sid}/rsvp", json={"email": "stranger@example.com", "response": "accepted"})).status_code == 422
    # an invitee's REPLY mail is applied (only for the address that sent it)
    ics = ("BEGIN:VCALENDAR\r\nMETHOD:REPLY\r\nBEGIN:VEVENT\r\nUID:" + sid + "@povu-erp-series\r\n"
           "RECURRENCE-ID;TZID=" + ctx.tz + ":20270329T090000\r\nATTENDEE;PARTSTAT=TENTATIVE:mailto:buyer@example.com\r\n"
           "END:VEVENT\r\nEND:VCALENDAR\r\n")
    assert not await svc.apply_reply(ctx.db, ics, "someone-else@example.com")
    assert await svc.apply_reply(ctx.db, ics, "buyer@example.com")
    await ctx.db.commit()
    occ = {o["date"]: o for o in (await _detail(ctx, sid))["occurrences"]}
    assert occ["2027-03-29"]["attendees"][0]["response"] == "tentative" and occ["2027-03-08"]["attendees"][0]["response"] == "accepted"
    # free/busy: ERP meetings + provider's own busy time
    await ctx.env.ctl({"events": [{"provider": ctx.provider, "id": "ext-1", "summary": "Private", "tz": "UTC",
                                   "start": {"dateTime": "2027-03-09T10:00:00+00:00"}, "end": {"dateTime": "2027-03-09T11:00:00+00:00"}}]})
    fb = (await ctx.api.get("/api/v1/meeting-series/free-busy", params={"start": "2027-03-08T00:00:00Z", "end": "2027-03-10T00:00:00Z"})).json()
    starts = [b["start"][:16] for b in fb["busy"]]
    assert "2027-03-09T10:00" in starts and any(s.startswith("2027-03-08T") for s in starts) and fb["provider"] == ctx.provider
    # the stand-alone meeting endpoints refuse a series occurrence
    mid = occ["2027-03-29"]["meeting_id"]
    assert (await ctx.api.patch(f"/api/v1/meetings/{mid}", json={"title": "Sneaky"})).status_code == 409
    assert (await ctx.api.delete(f"/api/v1/meetings/{mid}")).status_code == 409
    assert (await ctx.api.patch(f"/api/v1/meetings/{mid}", json={"notes": "Call notes are fine"})).status_code == 200
    # another user sees nothing and changes nothing
    stranger = await new_user(ctx.db, "stranger")
    other = ctx.env.api(stranger)
    assert (await other.get(f"/api/v1/meeting-series/{sid}")).status_code == 404
    assert (await other.patch(f"/api/v1/meeting-series/{sid}", json={"scope": "all", "title": "x"})).status_code == 404
    assert (await other.delete(f"/api/v1/meeting-series/{sid}")).status_code == 404
    # invalid input
    assert (await _create(ctx, rrule="FREQ=HOURLY")).status_code == 422
    assert (await _create(ctx, start="2027-03-14T02:30:00", time_zone="America/New_York")).status_code == 422   # gap on day one
    assert (await _create(ctx, time_zone="Mars/Olympus")).status_code == 422
    assert (await ctx.api.get("/api/v1/meeting-series")).json()[0]["id"] == sid
