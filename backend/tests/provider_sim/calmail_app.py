"""Local simulator for M49.S01.T001-T003: recurring calendar events, change notifications, shared / delegated mail.

Mount it next to the OAuth simulator (tests/provider_sim/app.py) and point the ERP at it:

    main = create_app(); cm = create_calmail_app(token_ok=main-token-check, deliver=...); main.mount("/cm", cm)
    settings: GOOGLE_CALENDAR_API_URL = base/cm/calendar/v3, MICROSOFT_GRAPH_BASE_URL = base/cm/graph/v1.0,
              GOOGLE_GMAIL_API_URL = base/cm/gmail/v1   (calmail_settings(base))

Contracts followed (public documentation):
- Google Calendar v3: events.insert/patch/delete with ``recurrence`` (RRULE, UNTIL in UTC), events.instances,
  events.list(singleEvents, syncToken -> 410 when gone, nextSyncToken), instance ids ``{id}_{YYYYMMDDTHHMMSSZ}`` with
  recurringEventId / originalStartTime, freeBusy.query, events.watch (api#channel: id, resourceId, expiration in ms),
  channels.stop, notification headers X-Goog-Channel-ID / -Token / -Resource-ID / -Resource-State / -Message-Number.
- Microsoft Graph v1.0: event recurrence {pattern, range}, /events/{id}/instances (seriesMasterId, originalStart),
  /calendarView/delta (@removed has the id only), /calendar/getSchedule, /subscriptions with the validationToken
  handshake (text/plain echo, 200), 4230-minute maximum, PATCH renew (404 once expired), notification and lifecycle
  payloads (subscriptionId, clientState, lifecycleEvent), /users/{id}/messages, /users/{id}/sendMail (403 without
  Send As), /me/sendMail JSON with from / sender (403 without Send on Behalf).
- Gmail v1: users.settings.sendAs.list (verificationStatus), users.messages.send (an unverified From alias is replaced
  by the caller's own address, as Gmail does), users/{other} only for a delegated (service account) caller.

Identity: a bearer token maps to an account e-mail (control ``identities``), so a shared mailbox can say who may read,
send as or send on behalf. Fault injection and time travel through /_control.
"""
from __future__ import annotations

import base64
import json
import secrets
from datetime import date, datetime, time, timedelta, timezone
from email import message_from_bytes, policy
from email.utils import getaddresses
from typing import Awaitable, Callable, Optional
from zoneinfo import ZoneInfo

from dateutil.rrule import DAILY, MONTHLY, WEEKLY, YEARLY, rrule, rrulestr, weekday
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

UTC = timezone.utc
Deliver = Callable[[str, str, dict, bytes], Awaitable[tuple[int, str, str]]]
MAX_SUB_MINUTES = 4230
_WD = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def calmail_settings(base: str) -> dict:
    base = base.rstrip("/") + "/cm"
    return {"GOOGLE_CALENDAR_API_URL": f"{base}/calendar/v3", "MICROSOFT_GRAPH_BASE_URL": f"{base}/graph/v1.0",
            "GOOGLE_GMAIL_API_URL": f"{base}/gmail/v1"}


def _utc(wall: datetime, tz: str) -> datetime:
    return wall.replace(tzinfo=ZoneInfo(tz)).astimezone(UTC).replace(tzinfo=None)


def _local(u: datetime, tz: str) -> datetime:
    return u.replace(tzinfo=UTC).astimezone(ZoneInfo(tz)).replace(tzinfo=None)


def _when(obj: dict, default_tz: str = "UTC") -> tuple[datetime, str]:
    """{dateTime, timeZone} -> (naive wall time in that zone, zone)."""
    tz = obj.get("timeZone") or default_tz
    raw = obj["dateTime"].replace("Z", "+00:00")
    if "." in raw:
        head, _, rest = raw.partition(".")
        tail = rest.lstrip("0123456789")
        raw = head + tail
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is not None:
        dt = dt.astimezone(ZoneInfo(tz)).replace(tzinfo=None)
    return dt, tz


def create_calmail_app(token_ok: Optional[Callable[[str], Optional[str]]] = None, deliver: Optional[Deliver] = None) -> FastAPI:
    """token_ok(token) -> "google" | "microsoft" | None. Default: any ``g-``/``m-`` prefixed token (standalone use)."""
    app = FastAPI(title="POVU calendar + shared mail simulator (synthetic, local only)")
    st: dict = {}

    def reset() -> None:
        st.clear()
        st.update(ev={"google": {}, "microsoft": {}}, ver=0, gone=False, channels={}, subs={}, msgno={}, tokens={},
                  default_email={"google": "rep1@povu-demo.test", "microsoft": "rep1@povu-demo.test"}, offset=0,
                  mail={}, sent=[], acl={}, hid=1000, page_size=50, faults=[], notified=[], validate=True)

    reset()

    def now() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=st["offset"])

    def tok_provider(authorization: Optional[str]) -> Optional[str]:
        t = (authorization or "").removeprefix("Bearer ").strip()
        if token_ok is not None:
            return token_ok(t)
        return "google" if t.startswith("g-") else "microsoft" if t.startswith("m-") else None

    def caller(authorization: Optional[str], provider: str) -> Optional[str]:
        if tok_provider(authorization) != provider:
            return None
        t = (authorization or "").removeprefix("Bearer ").strip()
        return st["tokens"].get(t) or st["default_email"][provider]

    def g401():
        return JSONResponse({"error": {"code": 401, "message": "Invalid Credentials", "status": "UNAUTHENTICATED"}}, 401)

    def m401():
        return JSONResponse({"error": {"code": "InvalidAuthenticationToken", "message": "Access token is invalid."}}, 401)

    def injected():
        if st["faults"]:
            f = st["faults"].pop(0)
            return JSONResponse({"error": "rate_limited" if f == 429 else "server_error"}, f, headers={"Retry-After": "1"} if f == 429 else {})
        return None

    # ── control plane ───────────────────────────────────────────────────────
    @app.post("/_control")
    async def control(request: Request):
        b = await request.json()
        for k in ("gone", "validate", "page_size"):
            if k in b:
                st["gone" if k == "gone" else k] = b[k]
        st["tokens"].update(b.get("identities") or {})
        st["default_email"].update(b.get("default_email") or {})
        st["faults"].extend(b.get("faults") or [])
        st["offset"] += int(b.get("advance_seconds", 0))
        for addr, rules in (b.get("acl") or {}).items():
            st["acl"].setdefault(addr.lower(), {}).update(rules)       # read / send_as / on_behalf / gmail_dwd / gmail_send_as
        for m in b.get("deliver") or []:
            st["hid"] += 1
            st["mail"].setdefault(m["mailbox"].lower(), []).append(
                {"id": f"m{st['hid']}", "raw": base64.b64decode(m["raw_b64"]), "hid": st["hid"]})
        for e in b.get("events") or []:                                  # an event created in the provider's own UI
            st["ver"] += 1
            wall, tz = _when(e["start"], e.get("tz", "UTC"))
            end, _ = _when(e["end"], tz)
            ev = st["ev"][e["provider"]].setdefault(e["id"], {"id": e["id"]})
            ev.update(summary=e.get("summary", "Busy"), tz=tz, wall=wall, dur=int((end - wall).total_seconds() // 60),
                      free=bool(e.get("free")), cancelled=bool(e.get("cancelled")), ver=st["ver"], recur=e.get("recur"))
        for c in b.get("instance_changes") or []:                         # user moved / cancelled one occurrence
            ev = _instance_patch(c["provider"], c["master"], c["orig"], c)
            if ev is None:
                return JSONResponse({"error": "no such instance"}, 404)
        if "expire" in b:                                                 # {"id": ..., "seconds_from_now": -5}
            at = now() + timedelta(seconds=b["expire"]["seconds_from_now"])
            for coll, key in ((st["channels"], "expires"), (st["subs"], "expires")):
                if b["expire"]["id"] in coll:
                    coll[b["expire"]["id"]][key] = at
        return {"ok": True}

    @app.post("/_control/reset")
    async def control_reset():
        reset()
        return {"ok": True}

    @app.get("/_control/state")
    async def control_state():
        return {"channels": {k: {"address": v["address"], "expires": v["expires"].isoformat()} for k, v in st["channels"].items()},
                "subs": {k: {"url": v["notificationUrl"], "expires": v["expires"].isoformat()} for k, v in st["subs"].items()},
                "sent": [{k: v for k, v in s.items() if k not in ("raw",)} for s in st["sent"]],
                "events": {p: [e for e in d.values() if not e.get("cancelled") and not e.get("series")] for p, d in st["ev"].items()}}

    @app.get("/_control/events/{provider}")
    async def control_events(provider: str):
        return [{"id": e["id"], "summary": e.get("summary"), "series": e.get("series"), "cancelled": e.get("cancelled", False),
                 "recur": bool(e.get("recur")), "start_utc": _utc(e["wall"], e["tz"]).isoformat() if e.get("wall") else None,
                 "tz": e.get("tz")} for e in st["ev"][provider].values()]

    @app.get("/_control/sent")
    async def control_sent():
        return [{"path": s["path"], "caller": s["caller"], "from": s["from"], "to": s["to"], "subject": s["subject"],
                 "sender": s.get("sender"), "json": s.get("json"), "raw_b64": base64.b64encode(s["raw"]).decode()} for s in st["sent"]]

    @app.post("/_control/notify")
    async def control_notify(request: Request):
        """Fire a notification at the registered callback (through ``deliver``) and return what was sent."""
        b = await request.json()
        if b["provider"] == "google":
            ch = st["channels"][b["channel_id"]]
            n = b.get("message_number") or st["msgno"].get(b["channel_id"], 0) + 1
            st["msgno"][b["channel_id"]] = max(n, st["msgno"].get(b["channel_id"], 0))
            headers = {"X-Goog-Channel-ID": b["channel_id"], "X-Goog-Channel-Token": b.get("token", ch["token"]),
                       "X-Goog-Channel-Expiration": ch["expires"].strftime("%a, %d %b %Y %H:%M:%S GMT"),
                       "X-Goog-Resource-ID": b.get("resource_id", ch["resourceId"]),
                       "X-Goog-Resource-State": b.get("state", "exists"), "X-Goog-Message-Number": str(n),
                       "X-Goog-Resource-URI": ch["resourceUri"]}
            url, body = ch["address"], b""
        else:
            sub = st["subs"][b["subscription_id"]]
            item = {"subscriptionId": b["subscription_id"], "subscriptionExpirationDateTime": sub["expires"].isoformat() + "Z",
                    "clientState": b.get("client_state", sub["clientState"]), "tenantId": "sim-tenant"}
            if b.get("lifecycle"):
                item["lifecycleEvent"] = b["lifecycle"]
                url = sub["lifecycleNotificationUrl"]
            else:
                item.update(changeType=b.get("change_type", "updated"), resource=f"Users/sim/Events/{secrets.token_hex(4)}",
                            resourceData={"@odata.type": "#Microsoft.Graph.Event", "id": secrets.token_hex(4)})
                url = sub["notificationUrl"]
            headers, body = {"Content-Type": "application/json"}, json.dumps({"value": [item]}).encode()
        out = {"url": url, "headers": headers, "body": body.decode()}
        if deliver is not None:
            status, text, _ct = await deliver("POST", url, headers, body)
            out.update(status=status, response=text)
        st["notified"].append(out)
        return out

    # ── recurrence ──────────────────────────────────────────────────────────
    def _rule(ev: dict):
        rec, wall, tz = ev["recur"], ev["wall"], ev["tz"]
        if isinstance(rec, list):                                          # Google: ["RRULE:FREQ=...;UNTIL=...Z"]
            text = next(x for x in rec if x.upper().startswith("RRULE:"))[6:]
            parts = []
            for p in text.split(";"):
                if p.upper().startswith("UNTIL="):
                    u = p[6:]
                    dt = datetime.strptime(u.rstrip("Z"), "%Y%m%dT%H%M%S" if "T" in u else "%Y%m%d")
                    p = "UNTIL=" + (_local(dt, tz) if u.endswith("Z") else dt).strftime("%Y%m%dT%H%M%S")
                parts.append(p)
            return rrulestr(";".join(parts), dtstart=wall)
        pat, rng = rec["pattern"], rec["range"]
        kw: dict = {"dtstart": wall, "interval": pat.get("interval", 1)}
        t = pat["type"]
        wds = [weekday(_WD.index(d)) for d in pat.get("daysOfWeek", [])]
        if t == "daily":
            freq = DAILY
        elif t == "weekly":
            freq, kw["byweekday"] = WEEKLY, wds
        elif t == "absoluteMonthly":
            freq, kw["bymonthday"] = MONTHLY, pat["dayOfMonth"]
        elif t == "relativeMonthly":
            n = {"first": 1, "second": 2, "third": 3, "fourth": 4, "last": -1}[pat["index"]]
            freq, kw["byweekday"] = MONTHLY, [d(n) for d in wds]
        else:
            freq, kw["bymonth"], kw["bymonthday"] = YEARLY, pat["month"], pat["dayOfMonth"]
        if rng["type"] == "numbered":
            kw["count"] = rng["numberOfOccurrences"]
        elif rng["type"] == "endDate":
            kw["until"] = datetime.combine(date.fromisoformat(rng["endDate"]), time(23, 59, 59))
        return rrule(freq, **kw)

    def instances(master: dict, lo: datetime, hi: datetime) -> list[dict]:
        """Instances of a master within [lo, hi) (naive UTC), overrides merged, cancelled kept (flag)."""
        out = []
        over = {e["orig"]: e for e in st["ev"][master["provider"]].values() if e.get("series") == master["id"]}
        for wall in _rule(master):
            orig = _utc(wall, master["tz"])
            if orig >= hi + timedelta(days=2):
                break
            o = over.get(orig)
            start = _utc(o["wall"], o["tz"]) if o and o.get("wall") else orig
            if o is not None and o.get("wall") is None:
                o = {**o, "wall": wall, "tz": master["tz"], "dur": master["dur"]}
            dur = (o or master).get("dur") or master["dur"]
            if not (start < hi and start + timedelta(minutes=dur) > lo):
                continue
            out.append({"orig": orig, "start": start, "end": start + timedelta(minutes=dur), "tz": (o or master).get("tz") or master["tz"],
                        "summary": (o or {}).get("summary") or master.get("summary"), "cancelled": bool(o and o.get("cancelled")),
                        "free": master.get("free", False), "ver": max(master["ver"], o["ver"] if o else 0),
                        "override": o is not None, "master": master})
        return out

    def inst_by_orig(m: dict, orig: datetime) -> Optional[dict]:
        return next((i for i in instances(m, orig - timedelta(days=120), orig + timedelta(days=120)) if i["orig"] == orig), None)

    def _instance_patch(provider: str, master_id: str, orig_iso: str, body: dict):
        m = st["ev"][provider].get(master_id)
        if m is None or not m.get("recur"):
            return None
        orig = datetime.fromisoformat(orig_iso.replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None)
        if inst_by_orig(m, orig) is None:
            return None
        iid = _iid(provider, m["id"], orig)
        st["ver"] += 1
        ev = st["ev"][provider].setdefault(iid, {"id": iid, "provider": provider, "series": m["id"], "orig": orig, "tz": m["tz"]})
        ev["ver"] = st["ver"]
        if body.get("cancelled"):
            ev["cancelled"] = True
        if body.get("start") and body.get("end"):
            ev["wall"], ev["tz"] = _when(body["start"], m["tz"])
            e2, _ = _when(body["end"], ev["tz"])
            ev["dur"] = int((e2 - ev["wall"]).total_seconds() // 60)
            ev["cancelled"] = False
        if body.get("summary") or body.get("subject"):
            ev["summary"] = body.get("summary") or body.get("subject")
        return ev

    def _iid(provider: str, master_id: str, orig: datetime) -> str:
        return f"{master_id}_{orig:%Y%m%dT%H%M%SZ}" if provider == "google" else f"{master_id}.{orig:%Y%m%d%H%M}"

    def _find_instance(provider: str, iid: str):
        for m in st["ev"][provider].values():
            if m.get("recur") and iid.startswith(m["id"] + ("_" if provider == "google" else ".")):
                stamp = iid[len(m["id"]) + 1:]
                for i in instances(m, now() - timedelta(days=800), now() + timedelta(days=800)):
                    if stamp == (f"{i['orig']:%Y%m%dT%H%M%SZ}" if provider == "google" else f"{i['orig']:%Y%m%d%H%M}"):
                        return m, i
        return None, None

    # ── Google Calendar ─────────────────────────────────────────────────────
    def g_out(ev: dict, inst: Optional[dict] = None) -> dict:
        if inst is not None:
            m = inst["master"]
            out = {"kind": "calendar#event", "id": _iid("google", m["id"], inst["orig"]),
                   "status": "cancelled" if inst["cancelled"] else "confirmed", "etag": str(inst["ver"]),
                   "recurringEventId": m["id"],
                   "originalStartTime": {"dateTime": inst["orig"].replace(tzinfo=UTC).isoformat(), "timeZone": m["tz"]}}
            if not inst["cancelled"]:
                out.update(summary=inst["summary"], transparency="transparent" if inst["free"] else "opaque",
                           start={"dateTime": inst["start"].replace(tzinfo=UTC).isoformat(), "timeZone": inst["tz"]},
                           end={"dateTime": inst["end"].replace(tzinfo=UTC).isoformat(), "timeZone": inst["tz"]})
            return out
        if ev.get("cancelled"):
            return {"id": ev["id"], "status": "cancelled"}
        s = _utc(ev["wall"], ev["tz"])
        out = {"kind": "calendar#event", "id": ev["id"], "status": "confirmed", "etag": str(ev["ver"]), "summary": ev.get("summary"),
               "transparency": "transparent" if ev.get("free") else "opaque",
               "start": {"dateTime": s.replace(tzinfo=UTC).isoformat(), "timeZone": ev["tz"]},
               "end": {"dateTime": (s + timedelta(minutes=ev["dur"])).replace(tzinfo=UTC).isoformat(), "timeZone": ev["tz"]}}
        if ev.get("recur"):
            out["recurrence"] = ev["recur"]
        if ev.get("priv"):
            out["extendedProperties"] = {"private": ev["priv"]}
        if ev.get("hangout"):
            out["hangoutLink"] = ev["hangout"]
        return out

    def g_write(body: dict, eid: Optional[str] = None) -> dict:
        st["ver"] += 1
        eid = eid or f"gev{st['ver']}"
        ev = st["ev"]["google"].setdefault(eid, {"id": eid, "provider": "google"})
        if "start" in body:
            ev["wall"], ev["tz"] = _when(body["start"], body["start"].get("timeZone") or "UTC")
            e2, _ = _when(body["end"], ev["tz"])
            ev["dur"] = int((e2 - ev["wall"]).total_seconds() // 60)
        if body.get("recurrence"):
            if not (body.get("start") or {}).get("timeZone") and not ev.get("tz"):
                raise ValueError("Missing time zone definition for start time.")
            ev["recur"] = body["recurrence"]
        ev["summary"] = body.get("summary", ev.get("summary"))
        ev["priv"] = (body.get("extendedProperties") or {}).get("private", ev.get("priv"))
        if body.get("conferenceData"):
            ev["hangout"] = f"https://meet.google.com/sim-{st['ver']}"
        ev.update(ver=st["ver"], cancelled=False, free=body.get("transparency") == "transparent")
        return ev

    def g_items(since: int, lo: datetime, hi: datetime) -> list[dict]:
        out = []
        for ev in list(st["ev"]["google"].values()):
            if ev.get("series"):
                if since and ev["ver"] > since:                          # override changed since the token
                    m = st["ev"]["google"][ev["series"]]
                    out += [g_out(m, inst_by_orig(m, ev["orig"]))]
                continue
            if ev.get("recur"):
                if ev["ver"] > since or not since:
                    if ev.get("cancelled"):
                        continue
                    out += [g_out(ev, i) for i in instances(ev, lo, hi)]      # showDeleted=true: cancelled ones are listed
            elif ev["ver"] > since and (since or not ev.get("cancelled")):
                out.append(g_out(ev))
        return out

    @app.get("/calendar/v3/calendars/primary/events")
    async def g_list(request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "google") is None:
            return g401()
        if (f := injected()) is not None:
            return f
        q = request.query_params
        if q.get("syncToken") and st["gone"]:
            st["gone"] = False
            return JSONResponse({"error": {"code": 410, "message": "Sync token is no longer valid, a full sync is required."}}, 410)
        since = int(q.get("syncToken") or 0)
        lo = datetime.fromisoformat(q["timeMin"].replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None) if q.get("timeMin") else now() - timedelta(days=60)
        hi = datetime.fromisoformat(q["timeMax"].replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None) if q.get("timeMax") else now() + timedelta(days=400)
        return {"kind": "calendar#events", "items": g_items(since, lo, hi), "nextSyncToken": str(st["ver"])}

    @app.post("/calendar/v3/calendars/primary/events")
    async def g_insert(request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "google") is None:
            return g401()
        try:
            return g_out(g_write(await request.json()))
        except ValueError as e:
            return JSONResponse({"error": {"code": 400, "message": str(e)}}, 400)

    @app.patch("/calendar/v3/calendars/primary/events/{eid}")
    async def g_patch(eid: str, request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "google") is None:
            return g401()
        body = await request.json()
        ev = st["ev"]["google"].get(eid)
        if ev is not None and not ev.get("cancelled") and not ev.get("series"):
            return g_out(g_write(body, eid))
        m, inst = _find_instance("google", eid)
        if m is None:
            return JSONResponse({"error": {"code": 404, "message": "Not Found"}}, 404)
        o = _instance_patch("google", m["id"], inst["orig"].isoformat() + "Z", body)
        return g_out(m, inst_by_orig(m, o["orig"]))

    @app.delete("/calendar/v3/calendars/primary/events/{eid}")
    async def g_delete(eid: str, authorization: Optional[str] = Header(None)):
        if caller(authorization, "google") is None:
            return g401()
        ev = st["ev"]["google"].get(eid)
        if ev is not None and not ev.get("series"):
            st["ver"] += 1
            ev.update(cancelled=True, ver=st["ver"])
            return Response(status_code=204)
        m, inst = _find_instance("google", eid)
        if m is None:
            return JSONResponse({"error": {"code": 404, "message": "Not Found"}}, 404)
        _instance_patch("google", m["id"], inst["orig"].isoformat() + "Z", {"cancelled": True})
        return Response(status_code=204)

    @app.get("/calendar/v3/calendars/primary/events/{eid}/instances")
    async def g_instances(eid: str, request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "google") is None:
            return g401()
        m = st["ev"]["google"].get(eid)
        if m is None or not m.get("recur") or m.get("cancelled"):
            return JSONResponse({"error": {"code": 404, "message": "Not Found"}}, 404)
        q = request.query_params
        lo = datetime.fromisoformat(q["timeMin"].replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None)
        hi = datetime.fromisoformat(q["timeMax"].replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None)
        show = q.get("showDeleted") == "true"
        return {"kind": "calendar#events", "items": [g_out(m, i) for i in instances(m, lo, hi) if show or not i["cancelled"]]}

    @app.post("/calendar/v3/freeBusy")
    async def g_freebusy(request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "google") is None:
            return g401()
        b = await request.json()
        lo = datetime.fromisoformat(b["timeMin"].replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None)
        hi = datetime.fromisoformat(b["timeMax"].replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None)
        busy = []
        for e in g_items(0, lo, hi):
            if e.get("status") == "cancelled" or e.get("transparency") == "transparent":
                continue
            s, en = (datetime.fromisoformat(e[k]["dateTime"]).astimezone(UTC) for k in ("start", "end"))
            if s.replace(tzinfo=None) < hi and en.replace(tzinfo=None) > lo:
                busy.append({"start": s.strftime("%Y-%m-%dT%H:%M:%SZ"), "end": en.strftime("%Y-%m-%dT%H:%M:%SZ")})
        return {"kind": "calendar#freeBusy", "timeMin": b["timeMin"], "timeMax": b["timeMax"],
                "calendars": {b["items"][0]["id"]: {"busy": busy}}}

    @app.post("/calendar/v3/calendars/primary/events/watch")
    async def g_watch(request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "google") is None:
            return g401()
        b = await request.json()
        if b.get("type") != "web_hook" or not b.get("address") or not b.get("id"):
            return JSONResponse({"error": {"code": 400, "message": "Invalid channel", "errors": [{"reason": "invalid"}]}}, 400)
        if b["id"] in st["channels"]:
            return JSONResponse({"error": {"code": 400, "message": "Channel id not unique", "errors": [{"reason": "channelIdNotUnique"}]}}, 400)
        exp = datetime.fromtimestamp(int(b["expiration"]) / 1000, UTC).replace(tzinfo=None) if b.get("expiration") else now() + timedelta(days=7)
        rid = "rid-" + secrets.token_hex(6)
        st["channels"][b["id"]] = {"address": b["address"], "token": b.get("token", ""), "expires": exp, "resourceId": rid,
                                   "resourceUri": f"https://www.googleapis.com/calendar/v3/calendars/primary/events?alt=json"}
        return {"kind": "api#channel", "id": b["id"], "resourceId": rid, "resourceUri": st["channels"][b["id"]]["resourceUri"],
                "token": b.get("token"), "expiration": str(int(exp.replace(tzinfo=UTC).timestamp() * 1000))}

    @app.post("/calendar/v3/channels/stop")
    async def g_stop(request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "google") is None:
            return g401()
        b = await request.json()
        ch = st["channels"].get(b.get("id"))
        if ch is None or ch["resourceId"] != b.get("resourceId"):
            return JSONResponse({"error": {"code": 404, "message": "Channel not found"}}, 404)
        del st["channels"][b["id"]]
        return Response(status_code=204)

    # ── Microsoft Graph calendar ────────────────────────────────────────────
    def _g7(u: datetime) -> str:
        return u.strftime("%Y-%m-%dT%H:%M:%S.0000000")

    def m_out(ev: dict, inst: Optional[dict] = None) -> dict:
        if inst is not None:
            m = inst["master"]
            iid = _iid("microsoft", m["id"], inst["orig"])
            if inst["cancelled"]:
                return {"id": iid, "@removed": {"reason": "deleted"}}
            return {"id": iid, "type": "exception" if inst["override"] else "occurrence", "seriesMasterId": m["id"],
                    "originalStart": inst["orig"].strftime("%Y-%m-%dT%H:%M:%SZ"), "subject": inst["summary"],
                    "start": {"dateTime": _g7(inst["start"]), "timeZone": "UTC"}, "end": {"dateTime": _g7(inst["end"]), "timeZone": "UTC"},
                    "showAs": "free" if inst["free"] else "busy", "@odata.etag": str(inst["ver"])}
        if ev.get("cancelled"):
            return {"id": ev["id"], "@removed": {"reason": "deleted"}}
        s = _utc(ev["wall"], ev["tz"])
        out = {"id": ev["id"], "subject": ev.get("summary"), "type": "seriesMaster" if ev.get("recur") else "singleInstance",
               "start": {"dateTime": _g7(s), "timeZone": "UTC"}, "end": {"dateTime": _g7(s + timedelta(minutes=ev["dur"])), "timeZone": "UTC"},
               "showAs": "free" if ev.get("free") else "busy", "@odata.etag": str(ev["ver"]), "transactionId": ev.get("tx")}
        if ev.get("recur"):
            out["recurrence"] = ev["recur"]
        if ev.get("teams"):
            out["onlineMeeting"] = {"joinUrl": f"https://teams.microsoft.com/l/meetup-join/sim-{ev['ver']}"}
        return out

    def m_write(body: dict, eid: Optional[str] = None) -> dict:
        st["ver"] += 1
        eid = eid or f"mev{st['ver']}"
        ev = st["ev"]["microsoft"].setdefault(eid, {"id": eid, "provider": "microsoft"})
        if "start" in body:
            ev["wall"], ev["tz"] = _when(body["start"], body["start"].get("timeZone") or "UTC")
            e2, _ = _when(body["end"], ev["tz"])
            ev["dur"] = int((e2 - ev["wall"]).total_seconds() // 60)
        if body.get("recurrence"):
            ev["recur"] = body["recurrence"]
        ev["summary"] = body.get("subject", ev.get("summary"))
        ev["tx"] = body.get("transactionId", ev.get("tx"))
        ev["teams"] = bool(body.get("isOnlineMeeting", ev.get("teams")))
        ev.update(ver=st["ver"], cancelled=False, free=body.get("showAs") == "free")
        return ev

    def m_items(since: int, lo: datetime, hi: datetime) -> list[dict]:
        out = []
        for ev in list(st["ev"]["microsoft"].values()):
            if ev.get("series"):
                if since and ev["ver"] > since:
                    m = st["ev"]["microsoft"][ev["series"]]
                    out += [m_out(m, inst_by_orig(m, ev["orig"]))]
                continue
            if ev.get("recur"):
                if (ev["ver"] > since or not since) and not ev.get("cancelled"):
                    out += [m_out(ev, i) for i in instances(ev, lo, hi) if not (i["cancelled"] and not since)]
            elif ev["ver"] > since and (since or not ev.get("cancelled")):
                out.append(m_out(ev))
        return out

    def win(q) -> tuple[datetime, datetime]:
        p = lambda k, d: datetime.fromisoformat(q[k].replace("Z", "+00:00")).astimezone(UTC).replace(tzinfo=None) if q.get(k) else d  # noqa: E731
        return p("startDateTime", now() - timedelta(days=60)), p("endDateTime", now() + timedelta(days=400))

    @app.get("/graph/v1.0/me")
    async def m_me(authorization: Optional[str] = Header(None)):
        who = caller(authorization, "microsoft")
        return m401() if who is None else {"mail": who, "userPrincipalName": who}

    @app.get("/graph/v1.0/me/calendarView/delta")
    async def m_delta(request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "microsoft") is None:
            return m401()
        if (f := injected()) is not None:
            return f
        q = request.query_params
        if q.get("$deltatoken") and st["gone"]:
            st["gone"] = False
            return JSONResponse({"error": {"code": "syncStateNotFound"}}, 410)
        lo, hi = win(q)
        since = int(q.get("$deltatoken") or 0)
        base = str(request.url.replace(query=""))
        return {"value": m_items(since, lo, hi), "@odata.deltaLink": f"{base}?$deltatoken={st['ver']}"}

    @app.post("/graph/v1.0/me/events")
    async def m_insert(request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "microsoft") is None:
            return m401()
        body = await request.json()
        same = next((e for e in st["ev"]["microsoft"].values() if body.get("transactionId") and e.get("tx") == body["transactionId"]), None)
        return JSONResponse(m_out(same or m_write(body)), 201)

    @app.patch("/graph/v1.0/me/events/{eid}")
    async def m_patch(eid: str, request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "microsoft") is None:
            return m401()
        body = await request.json()
        ev = st["ev"]["microsoft"].get(eid)
        if ev is not None and not ev.get("cancelled") and not ev.get("series"):
            return m_out(m_write(body, eid))
        m, inst = _find_instance("microsoft", eid)
        if m is None:
            return JSONResponse({"error": {"code": "ErrorItemNotFound"}}, 404)
        o = _instance_patch("microsoft", m["id"], inst["orig"].isoformat() + "Z", body)
        return m_out(m, inst_by_orig(m, o["orig"]))

    @app.delete("/graph/v1.0/me/events/{eid}")
    async def m_delete(eid: str, authorization: Optional[str] = Header(None)):
        if caller(authorization, "microsoft") is None:
            return m401()
        ev = st["ev"]["microsoft"].get(eid)
        if ev is not None and not ev.get("series"):
            st["ver"] += 1
            ev.update(cancelled=True, ver=st["ver"])
            return Response(status_code=204)
        m, inst = _find_instance("microsoft", eid)
        if m is None:
            return JSONResponse({"error": {"code": "ErrorItemNotFound"}}, 404)
        _instance_patch("microsoft", m["id"], inst["orig"].isoformat() + "Z", {"cancelled": True})
        return Response(status_code=204)

    @app.get("/graph/v1.0/me/events/{eid}/instances")
    async def m_instances(eid: str, request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "microsoft") is None:
            return m401()
        m = st["ev"]["microsoft"].get(eid)
        if m is None or not m.get("recur") or m.get("cancelled"):
            return JSONResponse({"error": {"code": "ErrorItemNotFound"}}, 404)
        lo, hi = win(request.query_params)
        return {"value": [m_out(m, i) for i in instances(m, lo, hi) if not i["cancelled"]]}

    @app.post("/graph/v1.0/me/calendar/getSchedule")
    async def m_schedule(request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "microsoft") is None:
            return m401()
        b = await request.json()
        lo, hi = (datetime.fromisoformat(b[k]["dateTime"].split(".")[0]) for k in ("startTime", "endTime"))
        items = [{"status": "busy", "start": e["start"], "end": e["end"]} for e in m_items(0, lo, hi)
                 if "@removed" not in e and e.get("showAs") != "free"]
        return {"value": [{"scheduleId": s, "availabilityView": "", "scheduleItems": items} for s in b["schedules"]]}

    # ── Graph subscriptions ─────────────────────────────────────────────────
    async def _validate(url: str) -> bool:
        if not st["validate"] or deliver is None:
            return True
        token = "Validation: Testing client application reachability for subscription Request-Id: " + secrets.token_hex(8)
        status, text, ct = await deliver("POST", f"{url}{'&' if '?' in url else '?'}validationToken={token}", {}, b"")
        return status == 200 and text == token and ct.startswith("text/plain")

    @app.post("/graph/v1.0/subscriptions")
    async def sub_create(request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "microsoft") is None:
            return m401()
        b = await request.json()
        bad = lambda msg: JSONResponse({"error": {"code": "ValidationError", "message": msg}}, 400)  # noqa: E731
        if not b.get("notificationUrl") or not b.get("resource") or not b.get("changeType"):
            return bad("Missing notificationUrl, resource or changeType.")
        if len(b.get("clientState") or "") > 128:
            return bad("clientState exceeds 128 characters.")
        try:
            exp = datetime.fromisoformat(b["expirationDateTime"].split(".")[0].rstrip("Z"))
        except (KeyError, ValueError):
            return bad("Invalid expirationDateTime.")
        if exp > now() + timedelta(minutes=MAX_SUB_MINUTES):
            return bad(f"Subscription expiration can only be {MAX_SUB_MINUTES} minutes in the future.")
        if not await _validate(b["notificationUrl"]) or (b.get("lifecycleNotificationUrl") and not await _validate(b["lifecycleNotificationUrl"])):
            return bad("Subscription validation request failed. Notification endpoint must respond with 200 OK to validation request.")
        sid = secrets.token_hex(16)
        st["subs"][sid] = {"notificationUrl": b["notificationUrl"], "lifecycleNotificationUrl": b.get("lifecycleNotificationUrl"),
                           "clientState": b.get("clientState"), "expires": exp, "resource": b["resource"]}
        return JSONResponse({"id": sid, "resource": b["resource"], "changeType": b["changeType"], "clientState": b.get("clientState"),
                             "notificationUrl": b["notificationUrl"], "lifecycleNotificationUrl": b.get("lifecycleNotificationUrl"),
                             "expirationDateTime": exp.strftime("%Y-%m-%dT%H:%M:%S.0000000Z")}, 201)

    @app.patch("/graph/v1.0/subscriptions/{sid}")
    async def sub_renew(sid: str, request: Request, authorization: Optional[str] = Header(None)):
        if caller(authorization, "microsoft") is None:
            return m401()
        s = st["subs"].get(sid)
        if s is None or s["expires"] <= now():
            st["subs"].pop(sid, None)
            return JSONResponse({"error": {"code": "ResourceNotFound", "message": "The object was not found."}}, 404)
        exp = datetime.fromisoformat((await request.json())["expirationDateTime"].split(".")[0].rstrip("Z"))
        if exp > now() + timedelta(minutes=MAX_SUB_MINUTES):
            return JSONResponse({"error": {"code": "ValidationError", "message": "Expiration too far in the future."}}, 400)
        s["expires"] = exp
        return {"id": sid, "expirationDateTime": exp.strftime("%Y-%m-%dT%H:%M:%S.0000000Z")}

    @app.delete("/graph/v1.0/subscriptions/{sid}")
    async def sub_delete(sid: str, authorization: Optional[str] = Header(None)):
        if caller(authorization, "microsoft") is None:
            return m401()
        if st["subs"].pop(sid, None) is None:
            return JSONResponse({"error": {"code": "ResourceNotFound"}}, 404)
        return Response(status_code=204)

    # ── mail: Gmail + Graph, personal and delegated ─────────────────────────
    def acl(addr: str, kind: str) -> list:
        return [x.lower() for x in st["acl"].get(addr.lower(), {}).get(kind, [])]

    def inbox(addr: str) -> list:
        return st["mail"].setdefault(addr.lower(), [])

    def record_sent(path: str, who: str, raw: bytes, js: Optional[dict] = None, frm: Optional[str] = None, sender: Optional[str] = None):
        if js is not None:
            m = js["message"]
            to = [r["emailAddress"]["address"] for r in m.get("toRecipients", [])]
            frm = (m.get("from") or {}).get("emailAddress", {}).get("address") or who
            sender = (m.get("sender") or {}).get("emailAddress", {}).get("address")
            subject = m.get("subject", "")
        else:
            msg = message_from_bytes(raw, policy=policy.default)
            to = [a for _, a in getaddresses([str(msg.get("To", ""))])]
            subject = str(msg.get("Subject", ""))
            frm = frm or (getaddresses([str(msg.get("From", ""))])[0][1] if msg.get("From") else who)
        st["sent"].append({"path": path, "caller": who, "from": (frm or who).lower(), "to": to, "subject": subject, "raw": raw,
                           "json": js, "sender": sender})

    # Gmail
    def gm_target(uid: str, who: str):
        if uid == "me" or uid.lower() == who.lower():
            return who
        if who.lower() in acl(uid, "gmail_dwd"):
            return uid.lower()
        return None

    def gm_denied():
        return JSONResponse({"error": {"code": 403, "message": "Delegation denied", "status": "PERMISSION_DENIED"}}, 403)

    @app.get("/gmail/v1/users/{uid}/profile")
    async def gm_profile(uid: str, authorization: Optional[str] = Header(None)):
        who = caller(authorization, "google")
        if who is None:
            return g401()
        t = gm_target(uid, who)
        return gm_denied() if t is None else {"emailAddress": t, "historyId": str(st["hid"])}

    @app.get("/gmail/v1/users/{uid}/settings/sendAs")
    async def gm_sendas(uid: str, authorization: Optional[str] = Header(None)):
        who = caller(authorization, "google")
        if who is None:
            return g401()
        out = [{"sendAsEmail": who, "isPrimary": True, "verificationStatus": "accepted"}]
        for addr, rules in st["acl"].items():
            for a in rules.get("gmail_send_as", []):
                if a["user"].lower() == who.lower():
                    out.append({"sendAsEmail": addr, "isPrimary": False, "displayName": addr, "treatAsAlias": False,
                                "verificationStatus": a.get("status", "accepted")})
        return {"sendAs": out}

    @app.get("/gmail/v1/users/{uid}/messages")
    async def gm_list(uid: str, maxResults: int = 100, authorization: Optional[str] = Header(None)):
        who = caller(authorization, "google")
        if who is None:
            return g401()
        t = gm_target(uid, who)
        if t is None:
            return gm_denied()
        msgs = list(reversed(inbox(t)))[:maxResults]
        return {"messages": [{"id": m["id"], "threadId": m["id"]} for m in msgs]}

    @app.get("/gmail/v1/users/{uid}/messages/{mid}")
    async def gm_get(uid: str, mid: str, authorization: Optional[str] = Header(None)):
        who = caller(authorization, "google")
        if who is None:
            return g401()
        t = gm_target(uid, who)
        if t is None:
            return gm_denied()
        m = next((x for x in inbox(t) if x["id"] == mid), None)
        return JSONResponse({"error": {"code": 404}}, 404) if m is None else {"id": mid, "raw": base64.urlsafe_b64encode(m["raw"]).decode().rstrip("=")}

    @app.get("/gmail/v1/users/{uid}/history")
    async def gm_history(uid: str, startHistoryId: int, pageToken: Optional[str] = None, authorization: Optional[str] = Header(None)):
        who = caller(authorization, "google")
        if who is None:
            return g401()
        t = gm_target(uid, who)
        if t is None:
            return gm_denied()
        newer = [m for m in inbox(t) if m["hid"] > startHistoryId]
        off = int(pageToken or 0)
        page = newer[off:off + st["page_size"]]
        body = {"history": [{"id": str(m["hid"]), "messagesAdded": [{"message": {"id": m["id"]}}]} for m in page], "historyId": str(st["hid"])}
        if off + st["page_size"] < len(newer):
            body["nextPageToken"] = str(off + st["page_size"])
        return body

    @app.post("/gmail/v1/users/me/messages/send")
    async def gm_send(request: Request, authorization: Optional[str] = Header(None)):
        who = caller(authorization, "google")
        if who is None:
            return g401()
        raw = base64.urlsafe_b64decode((await request.json())["raw"] + "==")
        msg = message_from_bytes(raw, policy=policy.default)
        frm = getaddresses([str(msg.get("From", ""))])[0][1].lower() if msg.get("From") else who
        ok = frm == who.lower() or any(a["user"].lower() == who.lower() and a.get("status", "accepted") == "accepted"
                                       for a in st["acl"].get(frm, {}).get("gmail_send_as", []))
        record_sent("gmail:me/messages/send", who, raw, frm=frm if ok else who)     # unverified alias: Gmail rewrites From
        return {"id": f"s{len(st['sent'])}", "threadId": "t1", "labelIds": ["SENT"]}

    # Graph mail
    def ms_target(addr: Optional[str], who: str):
        if addr is None or addr.lower() == who.lower() or who.lower() in acl(addr, "read"):
            return (addr or who).lower()
        return None

    def ms_denied():
        return JSONResponse({"error": {"code": "ErrorAccessDenied", "message": "Access is denied. Check credentials and try again."}}, 403)

    async def ms_delta(request: Request, addr: Optional[str], authorization: Optional[str]):
        who = caller(authorization, "microsoft")
        if who is None:
            return m401()
        t = ms_target(addr, who)
        if t is None:
            return ms_denied()
        q = request.query_params
        since = int(q.get("$deltatoken") or 0)
        newer = [m for m in inbox(t) if m["hid"] > since]
        off = int(q.get("$skiptoken") or 0)
        page = newer[off:off + st["page_size"]]
        base = str(request.url).split("?")[0]
        body = {"value": [{"id": m["id"]} for m in page]}
        if off + st["page_size"] < len(newer):
            body["@odata.nextLink"] = f"{base}?$skiptoken={off + st['page_size']}&$deltatoken={since}"
        else:
            body["@odata.deltaLink"] = f"{base}?$deltatoken={st['hid']}"
        return body

    async def ms_value(addr: Optional[str], mid: str, authorization: Optional[str]):
        who = caller(authorization, "microsoft")
        if who is None:
            return m401()
        t = ms_target(addr, who)
        if t is None:
            return ms_denied()
        m = next((x for x in inbox(t) if x["id"] == mid), None)
        return JSONResponse({"error": {"code": "ErrorItemNotFound"}}, 404) if m is None else Response(m["raw"], media_type="message/rfc822")

    @app.get("/graph/v1.0/me/mailFolders/inbox/messages/delta")
    async def ms_me_delta(request: Request, authorization: Optional[str] = Header(None)):
        return await ms_delta(request, None, authorization)

    @app.get("/graph/v1.0/users/{addr}/mailFolders/inbox/messages/delta")
    async def ms_u_delta(addr: str, request: Request, authorization: Optional[str] = Header(None)):
        return await ms_delta(request, addr, authorization)

    @app.get("/graph/v1.0/me/messages/{mid}/$value")
    async def ms_me_value(mid: str, authorization: Optional[str] = Header(None)):
        return await ms_value(None, mid, authorization)

    @app.get("/graph/v1.0/users/{addr}/messages/{mid}/$value")
    async def ms_u_value(addr: str, mid: str, authorization: Optional[str] = Header(None)):
        return await ms_value(addr, mid, authorization)

    @app.get("/graph/v1.0/users/{addr}/mailFolders/inbox")
    async def ms_u_inbox(addr: str, authorization: Optional[str] = Header(None)):
        who = caller(authorization, "microsoft")
        if who is None:
            return m401()
        return {"id": "inbox", "displayName": "Inbox"} if ms_target(addr, who) else ms_denied()

    @app.post("/graph/v1.0/me/sendMail")
    async def ms_me_send(request: Request, authorization: Optional[str] = Header(None)):
        who = caller(authorization, "microsoft")
        if who is None:
            return m401()
        raw = await request.body()
        if request.headers.get("content-type", "").startswith("application/json"):
            js = json.loads(raw)
            frm = ((js["message"].get("from") or {}).get("emailAddress") or {}).get("address", who).lower()
            sender = ((js["message"].get("sender") or {}).get("emailAddress") or {}).get("address")
            if frm != who.lower() and who.lower() not in acl(frm, "on_behalf") + acl(frm, "send_as"):
                return JSONResponse({"error": {"code": "ErrorSendOnBehalfOfDenied", "message": "Not allowed to send on behalf."}}, 403)
            record_sent("graph:me/sendMail", who, raw, js=js)
            return Response(status_code=202)
        mime = base64.b64decode(raw)
        msg = message_from_bytes(mime, policy=policy.default)
        frm = getaddresses([str(msg.get("From", ""))])[0][1].lower() if msg.get("From") else who
        if frm != who.lower() and who.lower() not in acl(frm, "send_as"):
            return JSONResponse({"error": {"code": "ErrorSendAsDenied", "message": "Send As denied."}}, 403)
        record_sent("graph:me/sendMail", who, mime, frm=frm)
        return Response(status_code=202)

    @app.post("/graph/v1.0/users/{addr}/sendMail")
    async def ms_u_send(addr: str, request: Request, authorization: Optional[str] = Header(None)):
        who = caller(authorization, "microsoft")
        if who is None:
            return m401()
        if addr.lower() != who.lower() and who.lower() not in acl(addr, "send_as"):
            return JSONResponse({"error": {"code": "ErrorSendAsDenied", "message": "The user account does not have Send As permission."}}, 403)
        raw = await request.body()
        if request.headers.get("content-type", "").startswith("application/json"):
            record_sent(f"graph:users/{addr}/sendMail", who, raw, js=json.loads(raw))
        else:
            record_sent(f"graph:users/{addr}/sendMail", who, base64.b64decode(raw), frm=addr.lower())
        return Response(status_code=202)

    app.state.cm = st
    return app
