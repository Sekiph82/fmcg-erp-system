"""M51.S01.T011 regression tests for the independent-review findings S1-S4, I1, C1-C5 (DB part needs M51_DB=1).
No network: crawler/lab/S3 pieces run on in-process transports and fakes; synthetic POVU data only."""
import asyncio
import os
import uuid

import httpx
import pytest

from app.core import provider_http
from app.services import m51_aeo_service as aeo
from app.services import m51_media_tools as mt
from app.services import m51_s3
from app.services import m51_seo_crawler as cr
from app.services import m51_storage as st
from tests.m51_media_common import client_for as media_client
from tests.m51_media_common import clean_scan, setv
from tests.m51_media_common import staff as media_staff

DB = pytest.mark.skipif(os.environ.get("M51_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
BASE = "/api/v1/media-studio"
PERMS = ("marketing.view", "marketing.create", "marketing.edit")


@pytest.fixture(autouse=True)
async def _cleanup():
    yield
    provider_http.set_test_transport(None)
    provider_http.set_resolver(None)
    if os.environ.get("M51_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


# ── S1 lab vitals ───────────────────────────────────────────────────────────

class _Route:
    def __init__(self, url):
        self.request = type("R", (), {"url": url})()
        self.done = None

    async def continue_(self):
        self.done = "continue"

    async def abort(self, reason):
        self.done = "abort"


@pytest.mark.asyncio
async def test_s1_playwright_route_guard_refuses_private_and_offorigin():
    async def go(url, local=True, host="127.0.0.1"):
        r = _Route(url)
        await cr._lab_request_guard(r, local, host)
        return r.done
    assert await go("http://127.0.0.1:8766/app.js") == "continue"          # own host, loopback only because egress=local
    assert await go("http://127.0.0.1:8766/app.js", local=False) == "abort"   # live mode: loopback is not public
    assert await go("http://169.254.169.254/latest/meta-data/") == "abort"    # cloud metadata
    assert await go("http://10.0.0.5/admin") == "abort"
    assert await go("https://example.org/track.js") == "abort"              # off-origin subresource or redirect target
    assert await go("file:///etc/passwd") == "abort"
    assert await go("data:text/plain,hi") == "continue"


def test_s1_lockdown_flags_pin_host_and_kill_other_addresses():
    f = cr.chrome_lockdown_flags("www.povu-demo.test", ["93.184.216.34"])
    assert "--host-resolver-rules=MAP www.povu-demo.test 93.184.216.34, MAP * ~NOTFOUND" in f
    assert "--proxy-server=http://127.0.0.1:9" in f and any(x.startswith("--proxy-bypass-list=<-loopback>;www.povu-demo.test") for x in f)


@DB
@pytest.mark.asyncio
async def test_s1_lab_own_only_and_subprocess_killed_on_timeout(monkeypatch):
    from tests.test_m51_s01_t004_seo_crawler import _allow, _setup
    from tests.m51_s01_seo_common import SIM, client_for, use_sim
    use_sim(monkeypatch)
    u = await _setup()
    monkeypatch.setattr(cr, "lab_tool", lambda: "lighthouse")
    monkeypatch.setattr(cr.shutil, "which", lambda n: "/fake/lighthouse")
    spawned = []

    class Hung:
        returncode = None

        def __init__(self):
            self.killed = False

        async def communicate(self):
            await asyncio.sleep(30)

        def kill(self):
            self.killed, self.returncode = True, -9

        async def wait(self):
            return self.returncode

    async def fake_exec(*a, **k):
        spawned.append(a)
        p = Hung()
        spawned.append(p)
        return p
    monkeypatch.setattr(cr.asyncio, "create_subprocess_exec", fake_exec)
    setv(monkeypatch, "SEO_LAB_TIMEOUT", 0.2)
    async with client_for(u) as c:
        await _allow(c, "http://127.0.0.1:8777", kind="AUTHORIZED_SOURCE", note="Partner agreed in writing 2026-11")
        r = await c.post("/api/v1/seo-pro/vitals/lab", json={"url": "http://127.0.0.1:8777/"})
        assert r.status_code == 403 and not spawned                      # someone else's site: no browser at all
        await _allow(c, SIM)
        lab = (await c.post("/api/v1/seo-pro/vitals/lab", json={"url": SIM + "/"})).json()
        assert lab["state"] == "ERROR" and spawned[1].killed             # timeout -> process killed in finally
        assert "--proxy-server=http://127.0.0.1:9" in " ".join(spawned[0])


# ── S2 CMS media detach, S3 restore, C1 multipart, C3 streaming ─────────────

async def _wav_upload(c, name, data, part):
    from tests.test_m51_s01_t010_storage import _upload
    s = await _upload(c, name, data, part)
    done = await c.post(f"{BASE}/storage/uploads/{s['id']}/complete")
    assert done.status_code == 200, done.text
    return done.json()


async def _env(monkeypatch, tmp_path, part=1000):
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    from tests.m51_media_common import ensure_tables
    await ensure_tables()
    clean_scan(monkeypatch)
    setv(monkeypatch, "MEDIA_STORAGE_PATH", str(tmp_path / "media"))
    setv(monkeypatch, "M51_STORAGE_BACKUP_PATH", str(tmp_path / "backup"))
    setv(monkeypatch, "M51_STORAGE_BACKEND", "local")
    setv(monkeypatch, "M51_STORAGE_PART_BYTES", part)
    setv(monkeypatch, "M51_STORAGE_QUOTA_BYTES", 1 << 40)
    async with AsyncSessionLocal() as db:
        maker, approver = await media_staff(db, "maker", PERMS), await media_staff(db, "approver", PERMS + ("marketing.approve",))
        await db.execute(text("DELETE FROM m51_storage_quotas"))
        await db.commit()
    return maker, approver


async def _cms_rows(key):
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.cms import CmsMedia
    async with AsyncSessionLocal() as db:
        return (await db.execute(select(CmsMedia).where(CmsMedia.storage_path == key))).scalars().all()


@DB
@pytest.mark.asyncio
async def test_s2_revoke_and_delete_unpublish_cms_media(monkeypatch, tmp_path):
    from tests.test_m51_s01_t010_storage import _key, wav_bytes
    maker, approver = await _env(monkeypatch, tmp_path)
    data = wav_bytes(2500)
    async with media_client(maker) as c, media_client(approver) as a:
        o = await _wav_upload(c, "episode.wav", data, 1000)
        key = await _key(o["id"])
        for how in ("revoke", "delete"):
            assert (await a.post(f"{BASE}/storage/objects/{o['id']}/approve")).status_code == 200   # after revoke it is DRAFT: approve again
            link = await a.post(f"{BASE}/storage/objects/{o['id']}/to-cms-media", json={"title": "POVU AllClean tips", "public": True})
            assert link.status_code == 201, link.text
            assert len(await _cms_rows(key)) == 1
            if how == "revoke":
                assert (await a.post(f"{BASE}/storage/objects/{o['id']}/revoke")).status_code == 200
            else:
                assert (await a.delete(f"{BASE}/storage/objects/{o['id']}")).status_code == 200
            assert await _cms_rows(key) == []                           # the CMS can no longer serve the file


@DB
@pytest.mark.asyncio
async def test_s3_restore_skips_deleted_and_reapproves_changed_c3_streams(monkeypatch, tmp_path):
    from pathlib import Path
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.m51_media import M51StorageObject
    from tests.test_m51_s01_t010_storage import _key, wav_bytes
    maker, approver = await _env(monkeypatch, tmp_path)
    async with media_client(maker) as c, media_client(approver) as a:
        same = await _wav_upload(c, "same.wav", wav_bytes(3500), 1000)
        changed = await _wav_upload(c, "changed.wav", wav_bytes(3100), 1000)
        gone = await _wav_upload(c, "gone.wav", wav_bytes(2200), 1000)
        for o in (same, changed, gone):
            assert (await a.post(f"{BASE}/storage/objects/{o['id']}/approve")).status_code == 200
        link = await a.post(f"{BASE}/storage/objects/{changed['id']}/to-cms-media", json={"title": "x"})
        assert link.status_code == 201
        bk = (await a.post(f"{BASE}/storage/backups")).json()
        be = st.get_backend("local")
        for o in (same, changed, gone):
            await be.delete(await _key(o["id"]))                        # bytes lost behind the database's back
        assert (await a.delete(f"{BASE}/storage/objects/{gone['id']}")).status_code == 200      # ... and one is deliberately deleted
        async with AsyncSessionLocal() as db:
            row = await db.get(M51StorageObject, uuid.UUID(changed["id"]))
            row.sha256 = "0" * 64                                       # content differs from the backup
            await db.commit()
        sizes, real_upload = [], st.LocalBackend.upload_part

        async def spy(self, key, uid, n, data):
            sizes.append(len(data))
            return await real_upload(self, key, uid, n, data)
        monkeypatch.setattr(st.LocalBackend, "upload_part", spy)

        def no_slurp(self):
            raise AssertionError("restore must stream, not read_bytes()")
        real_rb = Path.read_bytes
        monkeypatch.setattr(Path, "read_bytes", no_slurp)
        rs = (await a.post(f"{BASE}/storage/backups/{bk['id']}/restore")).json()
        monkeypatch.setattr(Path, "read_bytes", real_rb)
        assert same["id"] in rs["restored"] and changed["id"] in rs["restored"] and gone["id"] not in rs["restored"]
        assert {"id": gone["id"], "status": "DELETED"} in rs["skipped_state"]
        assert sizes and max(sizes) <= 1000                            # uploaded in part-size chunks, never whole-file
        async with AsyncSessionLocal() as db:
            g = await db.get(M51StorageObject, uuid.UUID(gone["id"]))
            s_ = await db.get(M51StorageObject, uuid.UUID(same["id"]))
            ch = await db.get(M51StorageObject, uuid.UUID(changed["id"]))
            assert g.status == "DELETED" and await be.size(g.key) is None            # not resurrected
            assert s_.status == "READY" and s_.approval == "APPROVED"               # unchanged and approved before the loss
            assert ch.status == "READY" and ch.approval == "DRAFT" and ch.approved_by is None   # changed: re-approval
        assert await _cms_rows(await _key(changed["id"])) == []                      # DRAFT again -> CMS row detached


@DB
@pytest.mark.asyncio
async def test_c1_parallel_parts_and_idempotent_complete(monkeypatch, tmp_path):
    from tests.test_m51_s01_t010_storage import wav_bytes
    maker, _ = await _env(monkeypatch, tmp_path)
    data = wav_bytes(8000)
    async with media_client(maker) as c:
        s = (await c.post(f"{BASE}/storage/uploads", json={"file_name": "p.wav", "total_size": len(data), "part_size": 1000})).json()
        assert s["parts_total"] == 8
        rs = await asyncio.gather(*[c.put(f"{BASE}/storage/uploads/{s['id']}/parts/{i}", content=data[(i - 1) * 1000:i * 1000]) for i in range(1, 9)])
        assert [r.status_code for r in rs] == [200] * 8
        from sqlalchemy import select
        from app.db.session import AsyncSessionLocal
        from app.models.m51_media import M51UploadSession
        async with AsyncSessionLocal() as db:
            assert sorted(int(k) for k in (await db.get(M51UploadSession, uuid.UUID(s["id"]))).parts) == list(range(1, 9))   # no part lost
        first, second, third = await asyncio.gather(*[c.post(f"{BASE}/storage/uploads/{s['id']}/complete") for _ in range(3)])
        assert [x.status_code for x in (first, second, third)] == [200, 200, 200], (first.text, second.text, third.text)
        assert {x.json()["id"] for x in (first, second, third)} == {first.json()["id"]} and first.json()["status"] == "READY"
        again = await c.post(f"{BASE}/storage/uploads/{s['id']}/complete")           # later repeat: same finished object
        assert again.status_code == 200 and again.json()["id"] == first.json()["id"]
        aborted = (await c.post(f"{BASE}/storage/uploads", json={"file_name": "q.wav", "total_size": 2000, "part_size": 1000})).json()
        await c.delete(f"{BASE}/storage/uploads/{aborted['id']}")
        assert (await c.post(f"{BASE}/storage/uploads/{aborted['id']}/complete")).status_code == 409


# ── C2 private S3 endpoint allow-list ───────────────────────────────────────

@pytest.mark.asyncio
async def test_c2_exact_private_endpoint_only(monkeypatch):
    setv(monkeypatch, "PROVIDER_EGRESS", "live")
    guard = provider_http._make_guard(provider_http._origin_key("https://minio.lan:9000"), False)
    await guard(httpx.Request("GET", "https://minio.lan:9000/bucket/key"))               # the configured endpoint: allowed
    for url in ("https://minio.lan:9001/x", "https://other.lan:9000/x", "http://minio.lan:9000/x", "https://127.0.0.1:9000/x"):
        with pytest.raises(provider_http.EgressBlocked):
            await guard(httpx.Request("GET", url))                                        # other port/host, or plain http: still refused
    plain = provider_http._make_guard(provider_http._origin_key("http://minio.lan:9000"), False)
    with pytest.raises(provider_http.EgressBlocked):                                      # TLS required unless explicitly allowed
        await plain(httpx.Request("GET", "http://minio.lan:9000/x"))
    provider_http.set_resolver(lambda host, port: asyncio.sleep(0, ["10.0.0.5"]))      # minio.lan is a private LAN host
    try:
        await provider_http._make_guard(provider_http._origin_key("http://minio.lan:9000"), True)(httpx.Request("GET", "http://minio.lan:9000/x"))
    finally:
        provider_http.set_resolver(None)
    await provider_http._make_guard(provider_http._origin_key("http://127.0.0.1:9000"), False)(httpx.Request("GET", "http://127.0.0.1:9000/x"))
    # the generic client still refuses a private host (nothing widened)
    with pytest.raises(provider_http.EgressBlocked):
        await provider_http._guard(httpx.Request("GET", "https://127.0.0.1:9000/x"))


@pytest.mark.asyncio
async def test_c2_pinned_backend_allows_only_the_allowed_host_private():
    provider_http.set_resolver(lambda host, port: asyncio.sleep(0, ["10.0.0.5"]))

    class Inner:
        async def connect_tcp(self, host, port, **k):
            return ("connected", host)
    pb = provider_http.PinnedBackend(Inner(), allow_host="minio.lan")
    assert await pb.connect_tcp("minio.lan", 9000) == ("connected", "10.0.0.5")           # still pinned to the resolved address
    with pytest.raises(provider_http.EgressBlocked):
        await pb.connect_tcp("evil.example", 9000)
    with pytest.raises(provider_http.EgressBlocked):
        await provider_http.PinnedBackend(Inner()).connect_tcp("minio.lan", 9000)


@pytest.mark.asyncio
async def test_c2_s3_client_passes_its_endpoint_to_the_client(monkeypatch):
    seen = {}

    def fake(**kw):
        seen.update(kw)
        raise RuntimeError("stop")
    monkeypatch.setattr(m51_s3, "provider_client", fake)
    with pytest.raises(RuntimeError):
        await m51_s3.S3Client("https://minio.lan:9000/", "b", "ak", "sk", allow_private=True).head("k")
    assert seen["allow_endpoint"] == "https://minio.lan:9000" and seen["allow_plain_http"] is True


# ── C4 crawler ──────────────────────────────────────────────────────────────

def _mock_site(monkeypatch, robots_status, robots_text="", pages=None):
    hits = []
    pages = pages or {}

    def handler(req: httpx.Request):
        hits.append(req.url.path)
        if req.url.path == "/robots.txt":
            return httpx.Response(robots_status, text=robots_text)
        if req.url.path in pages:
            return pages[req.url.path]
        return httpx.Response(200, text="<html lang='en'><head><title>POVU</title></head><body><h1>POVU AllClean 1 L</h1></body></html>",
                              headers={"content-type": "text/html"})
    setv(monkeypatch, "PROVIDER_EGRESS", "local")
    provider_http.set_test_transport(httpx.MockTransport(handler))
    return hits


async def _crawl(site="http://127.0.0.1:8766"):
    from tests.test_m51_s01_t004_seo_crawler import _allow, _setup
    from tests.m51_s01_seo_common import client_for
    u = await _setup()
    async with client_for(u) as c:
        await _allow(c, site)
        r = await c.post("/api/v1/seo-pro/crawl", json={"origin": site})
        assert r.status_code == 201 or r.status_code == 200, r.text
        return (await c.get(f"/api/v1/seo-pro/crawls/{r.json()['id']}")).json()


@DB
@pytest.mark.asyncio
async def test_c4_robots_5xx_disallows_all_but_404_allows(monkeypatch):
    hits = _mock_site(monkeypatch, 503)
    d = await _crawl()
    assert d["status"] == "DONE" and "/" not in hits and "/sitemap.xml" not in hits        # nothing but robots.txt was requested
    assert {i["code"] for i in d["issues"]} >= {"ROBOTS_UNREACHABLE", "ROBOTS_BLOCKED"}
    hits = _mock_site(monkeypatch, 404)
    d = await _crawl()
    assert "/" in hits and "ROBOTS_UNREACHABLE" not in {i["code"] for i in d["issues"]}


@DB
@pytest.mark.asyncio
async def test_c4_non_http_redirect_is_a_page_issue_not_an_abort(monkeypatch):
    _mock_site(monkeypatch, 404, pages={"/": httpx.Response(302, headers={"location": "ftp://files.example.com/x"})})
    d = await _crawl()
    assert d["status"] == "DONE" and "REDIRECT_INVALID" in {i["code"] for i in d["issues"]}


@DB
@pytest.mark.asyncio
async def test_c4_robots_rechecked_for_redirect_targets(monkeypatch):
    hits = _mock_site(monkeypatch, 200, "User-agent: *\nDisallow: /private/", pages={"/": httpx.Response(301, headers={"location": "/private/x"})})
    d = await _crawl()
    assert "/private/x" not in hits
    assert any(i["code"] == "ROBOTS_BLOCKED" and "/private/x" in i["detail"] for i in d["issues"])


# ── C5 ffmpeg ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_c5_probe_kills_ffmpeg_on_timeout_and_whitelists_protocols(monkeypatch, tmp_path):
    seen = []

    class Hung:
        returncode = None
        killed = False

        async def communicate(self):
            await asyncio.sleep(30)

        def kill(self):
            self.killed, self.returncode = True, -9

        async def wait(self):
            return self.returncode
    p = Hung()

    async def fake_exec(*a, **k):
        seen.append(a)
        return p
    monkeypatch.setattr(mt, "ffmpeg", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(mt.asyncio, "create_subprocess_exec", fake_exec)
    setv(monkeypatch, "M51_MEDIA_PROBE_TIMEOUT", 0.1)
    with pytest.raises(mt.MediaError) as e:
        await mt.probe_duration(tmp_path / "x.mp4")
    assert e.value.status == 504 and p.killed
    a = list(seen[0])
    assert a[a.index("-i") - 2:a.index("-i")] == ["-protocol_whitelist", "file"]
    assert mt.with_input_whitelist(["-ss", "1", "-i", "a", "-y", "b"]) == ["-ss", "1", "-protocol_whitelist", "file", "-i", "a", "-y", "b"]


# ── I1 AEO monthly cap ──────────────────────────────────────────────────────

async def _aeo_set(db, name="Cap test"):
    return await aeo.create_set(db, "tester", {"name": name, "locale": "en", "prompts": ["best hand wash powder"], "brand_terms": ["POVU"],
                                               "provider": "simulator", "samples_per_prompt": 1, "consent_confirmed": True})


@DB
@pytest.mark.asyncio
async def test_i1_failed_attempts_count_and_unused_reservation_is_released(monkeypatch):
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    from tests.m51_s01_seo_common import ensure_tables
    from app.services import ai_provider as ai
    monkeypatch.setattr(ai, "MAX_RETRY_SLEEP_S", 0.001)
    setv(monkeypatch, "PROVIDER_EGRESS", "local")
    setv(monkeypatch, "AEO_MONTHLY_CALL_CAP", 6)
    await ensure_tables()
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM m51_aeo_prompt_sets"))
        s = await _aeo_set(db)
        await db.commit()
        monkeypatch.setattr(aeo, "_override", ai.ScriptedProvider(script=[500] * 50))
        r1 = await aeo.run(db, s, "tester")
        await db.commit()
        assert r1.status == "FAILED" and r1.calls == 3 and await aeo.month_calls(db) == 3     # 3 failed attempts all counted
        r2 = await aeo.run(db, s, "tester")
        await db.commit()
        assert r2.calls == 3 and await aeo.month_calls(db) == 6
        with pytest.raises(aeo.AeoError) as e:                                                 # cap used up by failed attempts too
            await aeo.run(db, s, "tester")
        assert e.value.status == 409
        monkeypatch.setattr(aeo, "_override", ai.ScriptedProvider())
        setv(monkeypatch, "AEO_MONTHLY_CALL_CAP", 1000)
        r3 = await aeo.run(db, s, "tester")
        await db.commit()
        assert r3.status == "DONE" and r3.calls == 1 and await aeo.month_calls(db) == 7        # reserved 3, used 1, 2 released


@DB
@pytest.mark.asyncio
async def test_i1_concurrent_runs_cannot_both_pass_the_cap(monkeypatch):
    from sqlalchemy import text
    from app.db.session import AsyncSessionLocal
    from tests.m51_s01_seo_common import ensure_tables
    from app.services import ai_provider as ai
    setv(monkeypatch, "PROVIDER_EGRESS", "local")
    setv(monkeypatch, "AEO_MONTHLY_CALL_CAP", 5)                  # one run reserves 1 prompt x 1 sample x 3 attempts = 3
    await ensure_tables()
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM m51_aeo_prompt_sets"))
        s = await _aeo_set(db)
        await db.commit()
        sid = s.id

    class Slow(ai.BaseAIProvider):
        async def generate_text(self, prompt, system=None):
            await asyncio.sleep(0.2)
            return ai.AIResponse(text="POVU AllClean", provider="simulator", model="slow", prompt_tokens=1, completion_tokens=1, latency_ms=1)
    monkeypatch.setattr(aeo, "_override", Slow())

    async def one():
        async with AsyncSessionLocal() as db:
            from app.models.m51_seo import M51AeoPromptSet
            try:
                r = await aeo.run(db, await db.get(M51AeoPromptSet, sid), "tester")
                await db.commit()
                return r.status
            except aeo.AeoError as e:
                return e.status
    out = await asyncio.gather(one(), one())
    assert sorted(map(str, out)) == ["422", "DONE"], out


# ── S4 approver must not be an editor ───────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_s4_component_approver_is_not_any_editor_since_last_approval():
    from app.db.session import AsyncSessionLocal
    from tests.test_m51_s01_t001_layout_editor import _user, client, login, people
    a, b, _ = await people()
    async with AsyncSessionLocal() as db:
        e1 = await _user(db, ("marketing.view", "marketing.create", "marketing.edit", "marketing.approve"), "editor1")
        e2 = await _user(db, ("marketing.view", "marketing.create", "marketing.edit", "marketing.approve"), "editor2")
        await db.commit()
    base = "/api/v1/cms-layout"
    async with client() as ca, client() as cb, client() as c1, client() as c2:
        for cl, u in ((ca, a), (cb, b), (c1, e1), (c2, e2)):
            await login(cl, u)
        sid = (await cb.post("/api/v1/cms/sites", json={"name": "POVU Home Care", "key": f"povu{uuid.uuid4().hex[:5]}", "locales": ["en"]})).json()["id"]
        comp = (await ca.post(f"{base}/sites/{sid}/components", json={"preset": "promo-banner", "key": "promo"})).json()
        cid = comp["id"]
        draft = (await ca.get(f"{base}/components/{cid}")).json()["draft"]
        assert (await c1.patch(f"{base}/components/{cid}", json={"name": "Promo one"})).status_code == 200
        assert (await c2.patch(f"{base}/components/{cid}", json={"draft": draft})).status_code == 200      # updated_by is now editor2
        assert (await ca.post(f"{base}/components/{cid}/submit")).status_code == 200
        r = await c1.post(f"{base}/components/{cid}/approve", json={"ok": True})        # an earlier editor, not the last one
        assert r.status_code == 422 and "different person" in r.text
        assert (await c2.post(f"{base}/components/{cid}/approve", json={"ok": True})).status_code == 422   # the last editor
        assert (await ca.post(f"{base}/components/{cid}/approve", json={"ok": True})).status_code == 403  # no approve permission
        assert (await cb.post(f"{base}/components/{cid}/approve", json={"ok": True})).status_code == 200  # an independent approver


@pytest.mark.asyncio
async def test_c2_plain_http_only_to_private_storage_host():
    """M51 gate: the allow-private flag never permits plain http to a host that resolves publicly."""
    import httpx
    from app.core import provider_http as ph
    async def public(host, port):
        return ["93.184.216.34"]
    async def private(host, port):
        return ["10.1.2.3"]
    guard = ph._make_guard(("http", "s3.example.org", 9000), True)
    req = httpx.Request("GET", "http://s3.example.org:9000/bucket/key")
    ph.set_resolver(public)
    try:
        with pytest.raises(ph.EgressBlocked):
            await guard(req)
        ph.set_resolver(private)
        await guard(req)
    finally:
        ph.set_resolver(None)
