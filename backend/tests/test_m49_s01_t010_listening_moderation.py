"""M49.S01.T010 multichannel listening and moderation (DB part needs M49_DB=1).

Polling through official APIs only (LinkedIn comments, YouTube commentThreads, X mentions, Facebook/Instagram comments), webhook
replay ledger, assignment, reply draft -> second-person approval -> send (REPLIED only with the network's reply id), hide/delete only
where the API allows (the rest refused with the reason), sentiment with source evidence, author opt-out and retention.
TikTok exposes no comments to this integration: unavailable, never scraped."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.services import social_formats as sf
from tests.m49_social_helpers import (ALICE, BOB, DB, TEXT, VID, _dispose_engine, act, calls, ctl, drive, make_post, sim)  # noqa: F401

import time
XM = int(time.time() * 1000)          # numeric, increasing X ids
U = uuid.uuid4().hex[:6]            # external ids are globally unique per network: keep reruns independent
NEG = "Delivery was late and the bottle is leaking, I want a refund"


def test_moderation_matrix_states_what_is_unavailable_and_why():
    m = {n: sf.capabilities(n)["moderation"] for n in sf.NETWORKS}
    assert not m["tiktok"]["read"]["available"] and "no comments" in m["tiktok"]["read"]["note"]
    assert not m["linkedin"]["hide"]["available"] and "no hide" in m["linkedin"]["hide"]["note"]
    assert not m["x"]["delete"]["available"] and m["x"]["reply"]["available"] and "summoned" in m["x"]["reply"]["note"]
    assert m["instagram"]["hide"]["available"] and m["youtube"]["delete"]["available"] and not m["youtube"]["delete"]["verified"]


async def _live(db, network, **kw):
    from app.api.v1.endpoints import social as ep
    pid, ch = await make_post(db, network, **kw)
    await act(db, pid, "submit")
    out = await drive(db, pid)
    assert out["status"] == "PUBLISHED", out["error"]
    await ep.set_listening(uuid.UUID(ch["id"]), True, db, ALICE)
    return out, ch


async def _find(db, network, ext):
    from sqlalchemy import select

    from app.api.v1.endpoints import social as ep
    from app.models.crm import SocialItem
    i = await db.scalar(select(SocialItem).where(SocialItem.network == network, SocialItem.external_id == ext))
    return ep._item(i) if i else None


async def _items(db, **flt):
    from app.api.v1.endpoints import social as ep
    args = {"status": None, "sentiment": None, "network": None, "assigned_to": None, "kind": None, **flt}
    return (await ep.inbox(db=db, **args))["items"]


@DB
@pytest.mark.asyncio
async def test_polling_per_network_dedupes_tags_with_evidence_and_x_cursor(sim):
    from app.api.v1.endpoints import social_m49 as m
    from app.db.session import AsyncSessionLocal
    ctl(sim, li_asset_polls=0, yt_polls=0, processing_polls=0)
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        li, lch = await _live(db, "linkedin", fmt="text")
        sim["comments"][li["external_post_id"]] = [{"commentUrn": f"urn:li:comment:(a,{U})", "actor": "urn:li:person:anna", "message": {"text": NEG},
                                                    "created": {"time": int(now.timestamp() * 1000)}}]
        r = await m.poll(uuid.UUID(lch["id"]), db, ALICE)
        assert r["stored"] == 1
        assert (await m.poll(uuid.UUID(lch["id"]), db, ALICE))["stored"] == 0                          # same comment: not stored twice
        item = await _find(db, "linkedin", f"urn:li:comment:(a,{U})")
        assert item["sentiment"] == "NEGATIVE" and item["evidence"]["negative"] and item["evidence"]["source"]["network"] == "linkedin"
        assert item["evidence"]["source"]["via"] == "POLL" and item["retention_until"]
        yt, ych = await _live(db, "youtube", fmt="video", media=[VID], fopts={"title": "POVU demo", "made_for_kids": False})
        sim["comments"][yt["external_post_id"]] = [{"snippet": {"topLevelComment": {"id": f"yc1{U}", "snippet": {
            "authorDisplayName": "Baraka", "textOriginal": "Great product, thanks!", "publishedAt": now.isoformat()}}}}]
        assert (await m.poll(uuid.UUID(ych["id"]), db, ALICE))["stored"] == 1
        assert (await _find(db, "youtube", f"yc1{U}"))["sentiment"] == "POSITIVE"
        x, xch = await _live(db, "x", text="POVU AllClean is back")
        sim["x_mentions"] = [{"id": str(XM), "text": "@povu where can I find AllClean in Mombasa?", "author_id": "u1", "username": "wanjiku", "created_at": now.isoformat()}]
        assert (await m.poll(uuid.UUID(xch["id"]), db, ALICE))["stored"] == 1
        assert (await m.poll(uuid.UUID(xch["id"]), db, ALICE))["stored"] == 0
        sim["x_mentions"].append({"id": str(XM + 1), "text": "@povu thanks", "author_id": "u2", "username": "otieno", "created_at": now.isoformat()})
        assert (await m.poll(uuid.UUID(xch["id"]), db, ALICE))["stored"] == 1                          # since_id cursor: only the new mention
        assert {(await _find(db, "x", str(XM + k)))["kind"] for k in (0, 1)} == {"MENTION"}
        fb, fch = await _live(db, "facebook", fmt="text")
        sim["comments"][fb["external_post_id"]] = [{"id": f"fbc{U}", "message": "Nzuri sana", "from": {"name": "Zuri"}, "created_time": now.isoformat()}]
        assert (await m.poll(uuid.UUID(fch["id"]), db, ALICE))["stored"] == 1
        # TikTok: no comment API for this integration: visibly unavailable, nothing is scraped
        from app.api.v1.endpoints import social as ep
        ctl(sim, audited=False)
        tt, tch = await _live(db, "tiktok", fmt="video", media=[VID], tiktok={"privacy_level": "SELF_ONLY", "consent": True})
        res = await m.poll(uuid.UUID(tch["id"]), db, ALICE)
        assert res["stored"] == 0 and "no comments" in res["reason"]


@DB
@pytest.mark.asyncio
async def test_listening_is_opt_in_and_poll_off_when_not_enabled(sim):
    from app.api.v1.endpoints import social as ep
    from app.api.v1.endpoints import social_m49 as m
    from app.db.session import AsyncSessionLocal
    ctl(sim, processing_polls=0)
    async with AsyncSessionLocal() as db:
        pid, ch = await make_post(db, "x", text="POVU opt-in check")
        await act(db, pid, "submit")
        res = await m.poll(uuid.UUID(ch["id"]), db, ALICE)
        assert res["stored"] == 0 and "opt-in" in res["reason"]
        with pytest.raises(HTTPException) as e:
            await m.poll(uuid.uuid4(), db, ALICE)
        assert e.value.status_code == 404


@DB
@pytest.mark.asyncio
async def test_assignment_and_reply_needs_second_person_then_replied_with_network_id(sim):
    from app.api.v1.endpoints import social as ep
    from app.api.v1.endpoints import social_m49 as m
    from app.db.session import AsyncSessionLocal
    ctl(sim, yt_polls=0)
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        yt, ch = await _live(db, "youtube", fmt="video", media=[VID], fopts={"title": "POVU demo", "made_for_kids": False})
        sim["comments"][yt["external_post_id"]] = [{"snippet": {"topLevelComment": {"id": f"yc9{U}", "snippet": {
            "authorDisplayName": "Neema", "textOriginal": NEG, "publishedAt": now.isoformat()}}}}]
        await m.poll(uuid.UUID(ch["id"]), db, ALICE)
        item = await _find(db, "youtube", f"yc9{U}")
        iid = uuid.UUID(item["id"])
        a = await ep.update_item(iid, ep.ItemPatch(assigned_to="rep1"), db, ALICE)
        assert a["status"] == "ASSIGNED" and item["id"] in [i["id"] for i in await _items(db, assigned_to="rep1")]
        with pytest.raises(HTTPException) as e:
            await m.reply_action(iid, "send", db, ALICE)
        assert e.value.status_code == 409                                                       # no approved draft
        with pytest.raises(HTTPException):
            await m.reply_action(iid, "request", db, ALICE)                                     # nothing drafted yet
        await ep.update_item(iid, ep.ItemPatch(reply_draft="Sorry about the late delivery; please DM your order number."), db, ALICE)
        assert (await m.reply_action(iid, "request", db, ALICE))["reply_status"] == "PENDING"
        with pytest.raises(HTTPException) as e:
            await m.reply_action(iid, "approve", db, ALICE)                                     # the requester cannot approve
        assert e.value.status_code == 403
        assert (await m.reply_action(iid, "approve", db, BOB))["reply_status"] == "APPROVED"
        edited = await ep.update_item(iid, ep.ItemPatch(reply_draft="Edited after approval."), db, ALICE)
        assert edited["reply_status"] == "DRAFT" and edited["reply_approved_by"] is None       # an edit voids the approval
        await m.reply_action(iid, "request", db, ALICE)
        await m.reply_action(iid, "approve", db, BOB)
        sent = await m.reply_action(iid, "send", db, BOB)
        assert sent["reply_status"] == "SENT" and sent["status"] == "REPLIED" and sent["reply_external_id"].startswith("ytc")
        assert sim["replies"][-1]["to"] == f"yc9{U}" and sim["replies"][-1]["text"] == "Edited after approval."
        with pytest.raises(HTTPException):
            await m.reply_action(iid, "send", db, BOB)                                          # not sent twice


@DB
@pytest.mark.asyncio
async def test_reply_rules_per_network_x_summon_linkedin_parent_unsupported_tiktok(sim):
    from app.api.v1.endpoints import social as ep
    from app.api.v1.endpoints import social_m49 as m
    from app.db.session import AsyncSessionLocal
    from app.services import social_service as ss
    ctl(sim, li_asset_polls=0)
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        li, lch = await _live(db, "linkedin", fmt="text")
        sim["comments"][li["external_post_id"]] = [{"commentUrn": f"urn:li:comment:(p,{U})", "actor": "urn:li:person:joy", "message": {"text": "Is it available in Kisumu?"},
                                                    "created": {"time": int(now.timestamp() * 1000)}}]
        await m.poll(uuid.UUID(lch["id"]), db, ALICE)
        iid = uuid.UUID((await _find(db, "linkedin", f"urn:li:comment:(p,{U})"))["id"])
        await ep.update_item(iid, ep.ItemPatch(reply_draft="Yes, through our Kisumu distributor."), db, ALICE)
        await m.reply_action(iid, "request", db, ALICE)
        await m.reply_action(iid, "approve", db, BOB)
        out = await m.reply_action(iid, "send", db, BOB)
        assert out["status"] == "REPLIED" and sim["replies"][-1]["to"] == f"urn:li:comment:(p,{U})"      # parentComment
        # an X comment that is not a mention cannot be answered on self-serve tiers
        x, xch = await _live(db, "x", text="POVU X post")
        ch = await db.get(ss.SocialChannel, uuid.UUID(xch["id"]))
        await ss._store(db, ch, "x", "COMMENT", f"9{U}", author="someone", text="nice")
        await db.commit()
        xi = await _find(db, "x", f"9{U}")
        xid = uuid.UUID(xi["id"])
        await ep.update_item(xid, ep.ItemPatch(reply_draft="Thanks!"), db, ALICE)
        await m.reply_action(xid, "request", db, ALICE)
        await m.reply_action(xid, "approve", db, BOB)
        res = await m.reply_action(xid, "send", db, BOB)
        assert res["reply_status"] == "FAILED" and "mentioned" in res["reply_error"] and not (sim["replies"] and sim["replies"][-1]["to"] == f"9{U}")
        # TikTok: nothing can be sent, and the UI shows why
        tch = await db.get(ss.SocialChannel, uuid.UUID((await make_post(db, "tiktok", fmt="video", media=[VID], approve=False))[1]["id"]))
        await ss._store(db, tch, "tiktok", "COMMENT", f"tt{U}", author="a", text="hello")
        await db.commit()
        ti = await _find(db, "tiktok", f"tt{U}")
        assert not ti["ops"]["reply"]["available"] and "No comment API" in ti["ops"]["reply"]["reason"]
        with pytest.raises(HTTPException) as e:
            await m.reply_action(uuid.UUID(ti["id"]), "request", db, ALICE)
        assert e.value.status_code == 409


@DB
@pytest.mark.asyncio
async def test_hide_and_delete_only_where_allowed_and_confirmed_by_the_network(sim, monkeypatch):
    from app.api.v1.endpoints import social_m49 as m
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.services import social_service as ss
    ctl(sim, processing_polls=0, li_asset_polls=0)
    async with AsyncSessionLocal() as db:
        out = {}
        for n, fmt in (("facebook", "text"), ("instagram", "image"), ("linkedin", "text"), ("x", None)):
            media = [{"url": "https://cdn.povu-demo.test/images/a.jpg", "kind": "image"}] if n == "instagram" else []
            o, ch = await _live(db, n, fmt=fmt, media=media)
            c = await db.get(ss.SocialChannel, uuid.UUID(ch["id"]))
            await ss._store(db, c, n, "COMMENT" if n != "x" else "MENTION", f"{n}-c{U}", parent=o["external_post_id"], author="visitor", text="spam spam")
            out[n] = uuid.UUID((await _find(db, n, f"{n}-c{U}"))["id"])
        await db.commit()
        body = m.ModerateIn(confirm=True, reason="spam link")
        with pytest.raises(HTTPException) as e:
            await m.moderate(out["facebook"], "hide", m.ModerateIn(confirm=False, reason="spam link"), db, ALICE)
        assert e.value.status_code == 422
        hid = await m.moderate(out["facebook"], "hide", body, db, ALICE)
        assert hid["provider_state"] == "HIDDEN" and hid["status"] == "HIDDEN" and f"facebook-c{U}" in sim["hidden"]
        assert (await m.moderate(out["instagram"], "hide", body, db, ALICE))["provider_state"] == "HIDDEN"
        assert (await m.moderate(out["x"], "hide", body, db, ALICE))["provider_state"] == "HIDDEN"
        with pytest.raises(HTTPException) as e:                                               # LinkedIn documents no hide
            await m.moderate(out["linkedin"], "hide", body, db, ALICE)
        assert e.value.status_code == 409 and "no hide" in e.value.detail
        with pytest.raises(HTTPException) as e:                                               # X: you cannot delete other people's posts
            await m.moderate(out["x"], "delete", body, db, ALICE)
        assert e.value.status_code == 409
        gone = await m.moderate(out["linkedin"], "delete", body, db, ALICE)
        assert gone["status"] == "DELETED" and gone["text"] is None and gone["author"] is None and f"linkedin-c{U}" in sim["deleted"]
        with pytest.raises(HTTPException) as e:
            await m.moderate(out["linkedin"], "delete", body, db, ALICE)                      # already deleted
        assert e.value.status_code == 409
        monkeypatch.setattr(settings, "SOCIAL_PUBLISHING_ENABLED", False)
        with pytest.raises(HTTPException) as e:
            await m.moderate(out["instagram"], "delete", body, db, ALICE)
        assert e.value.status_code == 409 and "SOCIAL_PUBLISHING_ENABLED" in e.value.detail


@DB
@pytest.mark.asyncio
async def test_meta_webhook_replay_and_deletion_optout_and_retention(sim):
    import json

    from app.api.v1.endpoints import social as ep
    from app.api.v1.endpoints import social_m49 as m
    from app.db.session import AsyncSessionLocal
    from app.services import social_listening as sl
    from app.services import social_service as ss
    async with AsyncSessionLocal() as db:
        pid, ch = await make_post(db, "facebook", fmt="text", approve=False)
        await ep.set_listening(uuid.UUID(ch["id"]), True, db, ALICE)
        raw = json.dumps({"object": "page", "entry": [{"id": ch["external_id"], "changes": [{"field": "feed", "value": {
            "item": "comment", "verb": "add", "comment_id": f"c{ch['external_id']}", "post_id": "p1", "message": "Great hand wash, thanks!",
            "from": {"name": "Amani Otieno"}, "created_time": 1_790_000_000}}]}]}).encode()
        assert await sl.first_delivery(db, "meta", raw) is True
        assert await sl.first_delivery(db, "meta", raw) is False                                # replayed delivery: processed once
        assert (await ss.ingest_meta(db, json.loads(raw)))["stored"] == 1
        assert (await ss.ingest_meta(db, json.loads(raw)))["stored"] == 0                       # and the item dedupes on its own id
        item = await _find(db, "facebook", f"c{ch['external_id']}")
        assert item["sentiment"] == "POSITIVE"
        # the author deletes the comment on Facebook
        rm = json.loads(raw)
        rm["entry"][0]["changes"][0]["value"]["verb"] = "remove"
        await ss.ingest_meta(db, rm)
        assert (await _find(db, "facebook", f"c{ch['external_id']}"))["text"] is None
        # opt-out: erase what we hold and drop future items from this author
        await db.commit()
        c = await db.get(ss.SocialChannel, uuid.UUID(ch["id"]))
        await ss._store(db, c, "facebook", "COMMENT", f"o1{U}", author=f"Baraka Mwangi {U}", text="please remove my data, bad service")
        await db.commit()
        res = await m.optout(m.OptOutIn(network="facebook", author=f"baraka mwangi {U}", reason="asked by email"), db, ALICE)
        assert res["erased"] == 1
        assert await ss._store(db, c, "facebook", "COMMENT", f"o2{U}", author=f"Baraka Mwangi {U}", text="again") is False
        # retention: past retention_until the personal content is erased, the row stays (no re-ingest)
        await ss._store(db, c, "facebook", "COMMENT", f"r1{U}", author="Wanjiru", text="stale delivery")
        await db.commit()
        it = await db.scalar(__import__("sqlalchemy").select(ss.SocialItem).where(ss.SocialItem.external_id == f"r1{U}"))
        it.retention_until = datetime.now(timezone.utc) - timedelta(days=1)
        await db.commit()
        assert (await m.retention(db, ALICE))["erased"] >= 1
        await db.refresh(it)
        assert it.text is None and it.author is None and it.status == "DELETED"


@DB
@pytest.mark.asyncio
async def test_viewer_cannot_moderate_and_csv_import_still_marked_import(sim):
    from app.api.v1.endpoints import social as ep
    from app.api.v1.endpoints import social_m49 as m
    from app.db.session import AsyncSessionLocal
    from tests.m49_social_helpers import VIEWER
    async with AsyncSessionLocal() as db:
        with pytest.raises(HTTPException) as e:
            await m.optout(m.OptOutIn(network="x", author="someone"), db, VIEWER)
        assert e.value.status_code == 403
        r = await ep.import_items(ep.ImportIn(csv=f"network,kind,external_id,author,text\ntiktok,COMMENT,imp-{U},Asha,Love the packaging\n"), db, ALICE)
        assert r["stored"] == 1
        item = await _find(db, "tiktok", f"imp-{U}")
        assert item["source"] == "IMPORT" and not item["ops"]["reply"]["available"]
