"""M47.S01.T007 Content Hub depth (unit + DB; the DB part needs M46_DB=1 and the cms_media page_id/poster_path columns).

AI page translation within the brand budget (fake provider) and the plain-copy fallback; post narration through the
local TTS adapter (NOT_AVAILABLE, fake engine → staff-only WAV linked to the page); AI image adapter (NOT_CONFIGURED,
mock → DRAFT creative the DAM refuses until approved); one-to-many remix inside the budget; CMS in configuration
bundles (export live pages → dry run → import as drafts into another site key); video poster + trim with ffmpeg
(NOT_AVAILABLE when missing; a real run on a generated clip when ffmpeg is installed). Synthetic POVU data only.
"""
import io
import json
import os
import shutil
import struct
import subprocess
import uuid
import wave
import zlib

import pytest

from tests.test_m46_s01_content_hub import DB, _client, _login, _people, _publish, _user


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _wav() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 800)
    return buf.getvalue()


def _png() -> bytes:
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + chunk(b"IEND", b"")


def _mount_poster_public():
    from app.main import app
    if not any(getattr(r, "path", "") == "/api/v1/public/cms/media/{media_id}/poster" for r in app.routes):
        from app.api.v1.endpoints.cms_poster_public import router   # the coordinator registers it in module_registry
        app.include_router(router, prefix="/api/v1/public/cms")


# ── unit ──────────────────────────────────────────────────────────────────────

def test_adapters_default_to_not_available(monkeypatch):
    from app.services import image_gen_adapter as ig
    from app.services import tts_adapter as tts
    monkeypatch.setenv("TTS_ENGINE", "espeak-ng")
    monkeypatch.setattr(tts.shutil, "which", lambda name: None)                 # configured but not installed
    assert tts.engine() is None and tts.status()["status"] == "NOT_AVAILABLE"
    monkeypatch.delenv("TTS_ENGINE")
    assert tts.status()["status"] == "NOT_AVAILABLE"
    assert ig.get_generator() is None and ig.status()["status"] == "NOT_CONFIGURED"


def test_translatable_walk_order():
    from app.services import cms_service as cms
    doc, _ = cms.validate_doc({"blocks": [{"type": "hero", "title": "POVU AllClean 1 L", "subtitle": "Fresh"},
                                          {"type": "faq", "items": [{"q": "Where?", "a": "At [Duka Moja](/shops)"}]},
                                          {"type": "button", "label": "Buy", "href": "/buy"}], "seo": {"meta_title": "POVU"}})
    seen = []
    cms._walk_texts(doc, lambda s: seen.append(s) or s.upper())
    assert seen == ["POVU AllClean 1 L", "Fresh", "Where?", "At [Duka Moja](/shops)", "Buy", "POVU"]
    assert doc["blocks"][2]["label"] == "BUY" and doc["blocks"][2]["href"] == "/buy"


# ── 1. AI-drafted page translation ────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_ai_translation_within_budget_and_copy_fallback(monkeypatch):
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.audit_log import AuditLog
    from app.services import ai_provider

    class Fake:
        async def generate_text(self, prompt, system=None):
            return ai_provider.AIResponse(text=json.dumps(["SW " + t for t in json.loads(prompt)]), provider="fake", model="f",
                                          prompt_tokens=300, completion_tokens=300)
    monkeypatch.setattr(ai_provider, "get_ai_provider", lambda: Fake())
    a, b, _ = await _people()
    async with _client() as ca, _client() as cb:
        await _login(ca, a)
        await _login(cb, b)
        rich = (await cb.post("/api/v1/content-studio/profiles", json={"name": f"POVU tr {uuid.uuid4().hex[:4]}", "monthly_budget": 0.05})).json()
        poor = (await cb.post("/api/v1/content-studio/profiles", json={"name": f"POVU zero {uuid.uuid4().hex[:4]}", "monthly_budget": 0})).json()
        sid = (await cb.post("/api/v1/cms/sites", json={"name": "POVU tr", "key": f"tr{uuid.uuid4().hex[:5]}", "locales": ["en", "sw", "tr"]})).json()["id"]
        pg = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "POVU WhiteCare 1 kg", "slug": "whitecare", "draft": {
            "blocks": [{"type": "heading", "level": 1, "text": "POVU WhiteCare 1 kg"}, {"type": "text", "text": "Ask at [Duka Moja](/shops)."},
                       {"type": "button", "label": "Order", "href": "/order"}],
            "seo": {"meta_title": "POVU WhiteCare", "meta_description": "Laundry care from POVU"}}})).json()
        r = await ca.post(f"/api/v1/cms/pages/{pg['id']}/translate", json={"locale": "sw", "ai": True, "profile_id": rich["id"]})
        assert r.status_code == 201, r.text
        sw = r.json()
        assert sw["engine"] == "fake" and sw["cost"] > 0 and sw["translation_state"] == "NEEDS_REVIEW" and sw["status"] == "DRAFT"
        d = (await ca.get(f"/api/v1/cms/pages/{sw['id']}")).json()
        blocks = d["draft"]["blocks"]
        assert blocks[0]["text"] == "SW POVU WhiteCare 1 kg" and blocks[1]["text"] == "SW Ask at [Duka Moja](/shops)." and blocks[2]["label"] == "SW Order"
        assert blocks[2]["href"] == "/order" and d["draft"]["seo"]["meta_title"] == "SW POVU WhiteCare" and d["live_version"] is None
        prof = [p for p in (await cb.get("/api/v1/content-studio/profiles")).json() if p["id"] == rich["id"]][0]
        assert prof["calls_this_month"] == 1 and prof["spent_this_month"] > 0                     # the atomic reservation was used
        # no budget → the plain copy, still a draft for review
        tr = (await ca.post(f"/api/v1/cms/pages/{pg['id']}/translate", json={"locale": "tr", "ai": True, "profile_id": poor["id"]})).json()
        assert tr["engine"] == "copy" and tr["cost"] == 0 and tr["translation_state"] == "NEEDS_REVIEW"
        assert (await ca.get(f"/api/v1/cms/pages/{tr['id']}")).json()["draft"]["blocks"][0]["text"] == "POVU WhiteCare 1 kg"
    async with AsyncSessionLocal() as db:
        logs = {x.target_id: x.details for x in (await db.execute(select(AuditLog).where(
            AuditLog.event_type == "cms.page.translation_started", AuditLog.target_id.in_([sw["id"], tr["id"]])))).scalars()}
        assert logs[sw["id"]]["engine"] == "fake" and logs[sw["id"]]["cost"] > 0 and logs[tr["id"]]["engine"] == "copy"


# ── 2. post narration ─────────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_narration_not_available_and_fake_engine(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services import tts_adapter as tts
    monkeypatch.setattr(settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    monkeypatch.delenv("TTS_ENGINE", raising=False)
    a, b, _ = await _people()
    async with _client() as ca, _client() as cb, _client() as anon:
        await _login(ca, a)
        await _login(cb, b)
        sid = (await cb.post("/api/v1/cms/sites", json={"name": "POVU blog", "key": f"nb{uuid.uuid4().hex[:5]}"})).json()["id"]
        pg = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "kind": "POST", "title": "Storing POVU AllClean", "slug": "storing",
                                                       "draft": {"blocks": [{"type": "text", "text": "Keep cartons out of the sun."}]}})).json()
        r = await ca.post(f"/api/v1/cms/pages/{pg['id']}/narrate")
        assert r.status_code == 409 and "NOT_AVAILABLE" in r.text
        assert (await ca.get("/api/v1/cms/tools")).json()["tts"]["status"] == "NOT_AVAILABLE"
        said = []

        async def fake_synth(text, locale):
            said.append((text, locale))
            return _wav()
        monkeypatch.setattr(tts, "engine", lambda: "fake")
        monkeypatch.setattr(tts, "synthesize", fake_synth)
        r = await ca.post(f"/api/v1/cms/pages/{pg['id']}/narrate")
        assert r.status_code == 201, r.text
        m = r.json()
        assert m["kind"] == "AUDIO" and m["mime"] == "audio/wav" and m["page_id"] == pg["id"] and m["public"] is False and m["access_list_id"] is None
        assert said == [("Storing POVU AllClean. Keep cartons out of the sun.", "en")]
        assert (await ca.get(f"/api/v1/cms/media/{m['id']}/file")).content[:4] == b"RIFF"
        assert (await anon.get(f"/api/v1/public/cms/media/{m['id']}/file")).status_code == 401    # staff-only until an approver decides
        assert (await ca.patch(f"/api/v1/cms/media/{m['id']}", json={"public": True})).status_code == 403
        assert (await cb.patch(f"/api/v1/cms/media/{m['id']}", json={"public": True})).status_code == 200
        assert (await anon.get(f"/api/v1/public/cms/media/{m['id']}/file")).status_code == 200


# ── 3. AI image adapter → draft creative ─────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_image_generation_not_configured_and_draft_creative(tmp_path, monkeypatch):
    from app.api.v1.endpoints.marketing_assets import _usable
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.documents import Document, DocumentCategory, DocumentStatus
    from app.services import image_gen_adapter as ig
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path))
    a, _, _ = await _people()
    async with _client() as ca:
        await _login(ca, a)
        body = {"prompt": "POVU AllClean 1 L bottle on a shop counter", "title": "POVU AllClean counter visual"}
        r = await ca.post("/api/v1/content-studio/images", json=body)
        assert r.status_code == 409 and "NOT_CONFIGURED" in r.text

        class Mock:
            name = "mock-image"

            async def generate(self, prompt):
                return _png()
        monkeypatch.setattr(ig, "get_generator", lambda: Mock())
        assert (await ca.get("/api/v1/content-studio/images/status")).json()["status"] == "AVAILABLE"
        r = await ca.post("/api/v1/content-studio/images", json=body)
        assert r.status_code == 201, r.text
        out = r.json()
        assert out["status"] == "DRAFT" and out["engine"] == "mock-image"
        assert out["document_id"] not in [x["id"] for x in (await ca.get("/api/v1/marketing-assets")).json()]
    async with AsyncSessionLocal() as db:
        d = await db.get(Document, uuid.UUID(out["document_id"]))
        assert d.category == DocumentCategory.MARKETING_CREATIVE and d.mime_type == "image/png" and d.approved_by_id is None
        assert _usable(d) is False                                            # the DAM refuses it while unapproved
        d.file_scan_status = "CLEAN"
        assert _usable(d) is False                                            # clean scan alone is not enough
        d.status = DocumentStatus.APPROVED
        assert _usable(d) is True                                             # only the DAM approval makes it usable
        await db.rollback()


# ── 4. one-to-many remix ──────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_remix_one_draft_per_channel_within_budget(monkeypatch):
    from app.services import ai_provider

    class Fake:
        async def generate_text(self, prompt, system=None):
            return ai_provider.AIResponse(text="POVU AllClean is made in Kenya [E:e1].", provider="fake", model="f",
                                          prompt_tokens=1500, completion_tokens=500)       # 0.02 per call = the reservation
    monkeypatch.setattr(ai_provider, "get_ai_provider", lambda: Fake())
    a, b, _ = await _people()
    async with _client() as ca, _client() as cb:
        await _login(ca, a)
        await _login(cb, b)
        prof = (await cb.post("/api/v1/content-studio/profiles", json={
            "name": f"POVU remix {uuid.uuid4().hex[:4]}", "monthly_budget": 0.05,
            "evidence": [{"id": "e1", "text": "POVU AllClean is made in Kenya", "source": "Plant QA register"}]})).json()
        src = (await ca.post("/api/v1/content-studio/drafts", json={"profile_id": prof["id"], "channel": "blog", "template": "product_launch",
                                                                    "brief": "Launch POVU AllClean 1 L", "evidence_ids": ["e1"]})).json()
        assert src["engine"] == "fake"                                        # spent 0.02 of 0.05
        assert (await ca.post(f"/api/v1/content-studio/drafts/{src['id']}/remix", json={"channels": ["fax"]})).status_code == 422
        r = await ca.post(f"/api/v1/content-studio/drafts/{src['id']}/remix", json={"channels": ["social", "sms", "email", "sms"]})
        assert r.status_code == 201, r.text
        out = r.json()
        assert [d["channel"] for d in out] == ["social", "sms", "email"] and all(d["source_id"] == src["id"] and d["status"] == "DRAFT" for d in out)
        assert [d["engine"] for d in out] == ["fake", "rules", "rules"]      # the budget gate stops AI after the cap
        assert len(out[0]["body"]) <= 280 and len(out[1]["body"]) <= 160
        assert all(h["action"] == "repurposed" for d in out for h in d["history"])
        await ca.post(f"/api/v1/content-studio/drafts/{out[0]['id']}/submit")
        assert (await ca.post(f"/api/v1/content-studio/drafts/{out[0]['id']}/decide", json={"ok": True})).status_code == 403   # own approval path


# ── 5. content sync through configuration bundles ─────────────────────────────

@DB
@pytest.mark.asyncio
async def test_cms_bundle_round_trip_into_another_site_key():
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.cms import CmsCta, CmsPage, CmsRedirect, CmsSite, CmsTable, CmsTableRow
    a, b, _ = await _people()
    async with AsyncSessionLocal() as db:
        adm = await _user(db, ("roles.manage",), "cfgadmin")
        await db.commit()
    src_key, dst_key = f"sy{uuid.uuid4().hex[:5]}", f"sz{uuid.uuid4().hex[:5]}"
    ghost = str(uuid.uuid4())
    async with _client() as ca, _client() as cb, _client() as cadm:
        await _login(ca, a)
        await _login(cb, b)
        await _login(cadm, adm)
        sid = (await cb.post("/api/v1/cms/sites", json={"name": "POVU sync", "key": src_key, "locales": ["en", "sw"]})).json()["id"]
        home = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "POVU home", "slug": "home", "draft": {
            "blocks": [{"type": "heading", "level": 1, "text": "POVU AllClean 1 L"}, {"type": "video", "media_id": ghost, "title": "Clip"}]}})).json()
        await ca.post(f"/api/v1/cms/pages/{home['id']}/submit")
        await _publish(cb, home["id"])
        await ca.patch(f"/api/v1/cms/pages/{home['id']}", json={"draft": {"blocks": [{"type": "text", "text": "unpublished edit"}]}})
        sw = (await ca.post(f"/api/v1/cms/pages/{home['id']}/translate", json={"locale": "sw"})).json()
        await ca.patch(f"/api/v1/cms/pages/{sw['id']}", json={"draft": {"blocks": [{"type": "heading", "level": 1, "text": "Maji ya POVU"}]}})
        await ca.post(f"/api/v1/cms/pages/{sw['id']}/submit")
        await _publish(cb, sw["id"])
        await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "Never live", "slug": "draft-only"})
        t = (await ca.post(f"/api/v1/cms/sites/{sid}/tables", json={"key": "shops", "name": "Shops", "columns": [{"key": "name"}]})).json()
        await ca.put(f"/api/v1/cms/tables/{t['id']}/rows", json={"rows": [{"slug": "duka-moja", "name": "Duka Moja"}]})
        await cb.post(f"/api/v1/cms/sites/{sid}/redirects", json={"from_path": "/old-home", "to_path": "/"})
        await cb.post(f"/api/v1/cms/sites/{sid}/ctas", json={"key": "order", "label": "Order POVU", "href": "/order"})

        assert (await ca.get("/api/v1/config-bundles/export?include_cms=true")).status_code == 403
        bundle = (await cadm.get("/api/v1/config-bundles/export?include_cms=true")).json()
        cmsb = bundle["items"]["cms"]
        mine = [p for p in cmsb["pages"] if p["site"] == src_key]
        assert sorted((p["locale"], p["path"]) for p in mine) == [("en", "/"), ("sw", "/")]          # live pages only
        en = next(p for p in mine if p["locale"] == "en")
        assert en["content"]["blocks"][0]["text"] == "POVU AllClean 1 L" and en["media_refs"] == [ghost]   # the LIVE version, media by reference
        assert "domain" not in json.dumps([s for s in cmsb["sites"] if s["key"] == src_key])

        body = {"bundle": bundle, "site_keys": {src_key: dst_key}}
        plan = (await cadm.post("/api/v1/config-bundles/plan", json=body)).json()
        cms_steps = [s for s in plan["steps"] if s["table"].startswith("cms_") and s["key"].startswith(dst_key)]
        assert {s["table"] for s in cms_steps} == {"cms_sites", "cms_tables", "cms_pages", "cms_redirects", "cms_ctas"}
        assert all(s["action"] == "create" for s in cms_steps)
        assert any(ghost in (s.get("detail") or "") for s in cms_steps if s["table"] == "cms_pages")
        async with AsyncSessionLocal() as db:
            assert (await db.execute(select(CmsSite).where(CmsSite.key == dst_key))).first() is None    # dry run wrote nothing
        r = await cadm.post("/api/v1/config-bundles/apply", json=body)
        assert r.status_code == 200, r.text
        async with AsyncSessionLocal() as db:
            dst = (await db.execute(select(CmsSite).where(CmsSite.key == dst_key))).scalar_one()
            pages = (await db.execute(select(CmsPage).where(CmsPage.site_id == dst.id))).scalars().all()
            assert sorted(p.locale for p in pages) == ["en", "sw"] and all(p.status == "DRAFT" and p.live_version_id is None for p in pages)
            assert len({p.translation_group for p in pages}) == 1                # hreflang link kept
            assert {p.locale: p.translation_state for p in pages} == {"en": "SOURCE", "sw": "NEEDS_REVIEW"}
            en_page = next(p for p in pages if p.locale == "en")
            assert en_page.draft["blocks"][0]["text"] == "POVU AllClean 1 L" and dst.domain is None and dst.domain_status == "LOCAL_ONLY"
            tb = (await db.execute(select(CmsTable).where(CmsTable.site_id == dst.id))).scalar_one()
            assert tb.published is False and (await db.execute(select(CmsTableRow.slug).where(CmsTableRow.table_id == tb.id))).scalar_one() == "duka-moja"
            assert (await db.execute(select(CmsRedirect.to_path).where(CmsRedirect.site_id == dst.id))).scalar_one() == "/"
            assert (await db.execute(select(CmsCta.href).where(CmsCta.site_id == dst.id))).scalar_one() == "/order"
            en_id = en_page.id
        again = (await cadm.post("/api/v1/config-bundles/plan", json=body)).json()
        assert all(s["action"] == "unchanged" for s in again["steps"] if s["key"].startswith(dst_key))
        await ca.patch(f"/api/v1/cms/pages/{en_id}", json={"draft": {"blocks": [{"type": "text", "text": "local change"}]}})
        upd = [s for s in (await cadm.post("/api/v1/config-bundles/plan", json=body)).json()["steps"] if s["key"] == f"{dst_key} / en / /"]
        assert upd[0]["action"] == "update" and upd[0]["changed"] == ["draft"]
        assert (await cadm.post("/api/v1/config-bundles/apply", json=body)).json()["updated"] >= 1
        d = (await ca.get(f"/api/v1/cms/pages/{en_id}")).json()
        assert d["draft"]["blocks"][0]["text"] == "POVU AllClean 1 L" and d["status"] == "DRAFT" and d["live_version"] is None   # never published


# ── 6. video poster + trim ────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_poster_and_trim(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services import cms_media_service as media
    monkeypatch.setattr(settings, "MEDIA_STORAGE_PATH", str(tmp_path / "media"))
    _mount_poster_public()
    real_ffmpeg = shutil.which("ffmpeg")
    a, b, _ = await _people()
    async with _client() as ca, _client() as cb, _client() as anon:
        await _login(ca, a)
        await _login(cb, b)
        fake = (await ca.post("/api/v1/cms/media", data={"title": "POVU crate clip"},
                              files={"file": ("clip.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200, "video/mp4")})).json()
        monkeypatch.setattr(media.shutil, "which", lambda name: None)
        r = await ca.post(f"/api/v1/cms/media/{fake['id']}/poster", json={"t": 0})
        assert r.status_code == 409 and "NOT_AVAILABLE" in r.text
        r = await ca.post(f"/api/v1/cms/media/{fake['id']}/trim", json={"start": 0, "end": 1})
        assert r.status_code == 409 and "NOT_AVAILABLE" in r.text
        monkeypatch.undo()
        monkeypatch.setattr(settings, "MEDIA_STORAGE_PATH", str(tmp_path / "media"))
        if not real_ffmpeg:
            pytest.skip("ffmpeg is not installed: the real poster/trim run is skipped (NOT_AVAILABLE path tested above)")
        clip = tmp_path / "povu.mp4"
        subprocess.run([real_ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=64x48:rate=10",
                        "-c:v", "mpeg4", "-f", "mp4", str(clip)], check=True, timeout=120)
        v = (await ca.post("/api/v1/cms/media", data={"title": "POVU line clip"}, files={"file": ("povu.mp4", clip.read_bytes(), "video/mp4")})).json()
        r = await ca.post(f"/api/v1/cms/media/{v['id']}/poster", json={"t": 0.5})
        assert r.status_code == 200, r.text
        assert r.json()["poster"] is True
        assert (await ca.get(f"/api/v1/cms/media/{v['id']}/poster")).content[:8] == b"\x89PNG\r\n\x1a\n"
        assert (await anon.get(f"/api/v1/public/cms/media/{v['id']}/poster")).status_code == 401      # follows the media's access
        await cb.patch(f"/api/v1/cms/media/{v['id']}", json={"public": True})
        pub = await anon.get(f"/api/v1/public/cms/media/{v['id']}/poster")
        assert pub.status_code == 200 and pub.content[:4] == b"\x89PNG"
        assert (await ca.post(f"/api/v1/cms/media/{v['id']}/poster", json={"t": 0})).status_code == 403   # served media: approver only
        assert (await ca.post(f"/api/v1/cms/media/{v['id']}/trim", json={"start": 1, "end": 0.5})).status_code == 422
        r = await ca.post(f"/api/v1/cms/media/{v['id']}/trim", json={"start": 0, "end": 1})
        assert r.status_code == 201, r.text
        t = r.json()
        assert t["id"] != v["id"] and t["public"] is False and t["access_list_id"] is None and t["mime"] == "video/mp4" and t["sha256"] != v["sha256"]
        orig = [m for m in (await ca.get("/api/v1/cms/media")).json() if m["id"] == v["id"]][0]
        assert orig["sha256"] == v["sha256"] and orig["size"] == v["size"]                          # original untouched
        assert (await ca.get(f"/api/v1/cms/media/{t['id']}/file")).content[4:8] == b"ftyp"
