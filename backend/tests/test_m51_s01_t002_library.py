"""M51.S01.T002 shared component / theme / template library through the real APIs (DB-gated: M51_DB=1).

Reuse across pages and locales, per-page override, two-person approval, versioning and rollback, site header/footer/theme
assignment with a per-page override, approved brand tokens and the read-only e-mail theme. Synthetic POVU data only.
"""
import pytest

from tests.test_m51_s01_t001_layout_editor import DB, _dispose_engine, client, login, people  # noqa: F401

import uuid


async def _publish(ca, cb, cid, note="ok"):
    assert (await ca.post(f"/api/v1/cms-layout/components/{cid}/submit")).status_code == 200
    assert (await cb.post(f"/api/v1/cms-layout/components/{cid}/approve", json={"ok": True})).status_code == 200
    r = await cb.post(f"/api/v1/cms-layout/components/{cid}/publish", json={"note": note})
    assert r.status_code == 200, r.text
    return r.json()


def _text_ids(draft):
    def walk(bs):
        for b in bs:
            yield b
            yield from walk(b.get("children") or [])
    return [b["id"] for b in walk(draft["blocks"]) if b["type"] == "text"]


@DB
@pytest.mark.asyncio
async def test_library_reuse_override_versions_rollback_layout_and_brand():
    a, b, r = await people()
    key = f"povu{uuid.uuid4().hex[:5]}"
    base = "/api/v1/cms-layout"
    async with client() as ca, client() as cb, client() as cr, client() as pub:
        await login(ca, a)
        await login(cb, b)
        await login(cr, r)
        sid = (await cb.post("/api/v1/cms/sites", json={"name": "POVU Home Care", "key": key, "locales": ["en", "sw"]})).json()["id"]
        assert (await cr.get(f"{base}/sites/{sid}/components")).status_code == 403

        # create from presets; validation errors are 422; duplicates 409; nested references are refused
        promo = (await ca.post(f"{base}/sites/{sid}/components", json={"preset": "promo-banner", "key": "promo"})).json()
        assert promo["kind"] == "COMPONENT" and promo["status"] == "DRAFT"
        assert (await ca.post(f"{base}/sites/{sid}/components", json={"preset": "promo-banner", "key": "promo"})).status_code == 409
        assert (await ca.post(f"{base}/sites/{sid}/components", json={"preset": "nope"})).status_code == 422
        assert (await ca.post(f"{base}/sites/{sid}/components", json={"name": "Loop", "kind": "SECTION", "draft": {"blocks": [{"type": "component", "key": "promo"}]}})).status_code == 422
        assert (await ca.post(f"{base}/sites/{sid}/components", json={"name": "Bad", "kind": "SECTION", "draft": {"blocks": [
            {"type": "text", "text": "x", "style": {"desktop": {"color": "#FF0000"}}}]}})).status_code == 422
        cid = promo["id"]
        detail = (await ca.get(f"{base}/components/{cid}")).json()
        tid = _text_ids(detail["draft"])[0]

        # two-person approval; nothing is live until published
        assert (await ca.post(f"{base}/components/{cid}/publish", json={})).status_code == 403
        assert (await cb.post(f"{base}/components/{cid}/publish", json={})).status_code == 422
        await _publish(ca, cb, cid, "v1")

        # reuse in two pages / two locales, the second page overrides the text and hides it on mobile
        def page(title, ov=None):
            blk = {"type": "component", "key": "promo"}
            if ov:
                blk["overrides"] = ov
            return {"site_id": sid, "title": title, "draft": {"blocks": [blk]}}
        home = (await ca.post("/api/v1/cms/pages", json={**page("POVU home"), "slug": "home"})).json()
        promo_page = (await ca.post("/api/v1/cms/pages", json={**page("Promotions", {tid: {"text": "Order POVU Hand Wash Powder 1 kg Pouch today.", "hide": ["mobile"]}}), "slug": "promotions"})).json()
        bad_ov = await ca.post("/api/v1/cms/pages", json=page("Bad override", {tid: {"type": "html"}}))
        assert bad_ov.status_code == 422
        sw = (await ca.post(f"/api/v1/cms/pages/{home['id']}/translate", json={"locale": "sw"})).json()
        for pid in (home["id"], promo_page["id"], sw["id"]):
            await ca.post(f"/api/v1/cms/pages/{pid}/submit")
            await cb.post(f"/api/v1/cms/pages/{pid}/approve", json={"ok": True})
            assert (await cb.post(f"/api/v1/cms/pages/{pid}/publish", json={})).status_code == 200

        async def live(path, loc="en"):
            return (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": path, "locale": loc})).json()
        txt = lambda doc: doc["blocks"][0]["blocks"][0]["children"][0]   # noqa: E731  component -> section -> text
        assert txt(await live("/"))["text"] == "Order POVU AllClean 1 L through your distributor."
        ov = txt(await live("/promotions"))
        assert ov["text"].startswith("Order POVU Hand Wash Powder") and ov["hide"] == ["mobile"] and ov["css"]["mobile"]["fontWeight"] == 600
        assert (await live("/", "sw"))["blocks"][0]["type"] == "component"
        used = (await ca.get(f"{base}/components/{cid}/usage")).json()
        assert {u["path"] for u in used["pages"]} >= {"/", "/promotions"} and {u["locale"] for u in used["pages"]} == {"en", "sw"}

        # per-locale variant in the component: Swahili pages show it, others keep the default
        sw_blocks = [{"type": "text", "text": "Agiza POVU AllClean 1 L kupitia msambazaji wako."}]
        e = await ca.patch(f"{base}/components/{cid}", json={"draft": {"blocks": detail["draft"]["blocks"], "locales": {"sw": sw_blocks}}})
        assert e.status_code == 200 and e.json()["status"] == "PUBLISHED"   # live v1 keeps serving; the edit is a draft
        assert (await live("/"))["blocks"][0]["blocks"][0]["children"][0]["text"].startswith("Order POVU AllClean")     # still v1 until published
        v2 = await _publish(ca, cb, cid, "v2 swahili")
        assert v2["version"] == 2
        assert (await live("/", "sw"))["blocks"][0]["blocks"][0]["text"].startswith("Agiza POVU AllClean")
        assert (await live("/"))["blocks"][0]["blocks"][0]["children"][0]["text"].startswith("Order POVU AllClean")      # default locale keeps the section
        # rollback to v1 re-publishes the old content for every page at once
        rb = await cb.post(f"{base}/components/{cid}/rollback", json={"version": 1})
        assert rb.status_code == 200 and rb.json()["version"] == 3
        assert (await live("/", "sw"))["blocks"][0]["blocks"][0]["children"][0]["text"].startswith("Order POVU AllClean")
        assert [v["version"] for v in (await ca.get(f"{base}/components/{cid}")).json()["versions"]] == [3, 2, 1]

        # header / footer / theme: kinds are checked, assignment is an approver decision, a page can opt out
        hdr = (await ca.post(f"{base}/sites/{sid}/components", json={"preset": "header-simple", "key": "main-header"})).json()
        ftr = (await ca.post(f"{base}/sites/{sid}/components", json={"preset": "footer-simple", "key": "main-footer"})).json()
        theme = (await ca.post(f"{base}/sites/{sid}/components", json={"preset": "povu-calm", "key": "calm"})).json()
        assert (await cb.put(f"{base}/sites/{sid}/layout", json={"header_key": "main-header"})).status_code == 422          # not published yet
        for c in (hdr, ftr, theme):
            await _publish(ca, cb, c["id"])
        assert (await cb.put(f"{base}/sites/{sid}/layout", json={"header_key": "main-footer"})).status_code == 422          # wrong kind
        assert (await ca.put(f"{base}/sites/{sid}/layout", json={"header_key": "main-header"})).status_code == 403
        lay = await cb.put(f"{base}/sites/{sid}/layout", json={"header_key": "main-header", "footer_key": "main-footer", "theme_key": "calm"})
        assert lay.status_code == 200 and lay.json()["theme_key"] == "calm"
        p = await live("/")
        assert p["layout"]["header"] and p["layout"]["footer"] and p["layout"]["tokens"]["colors"]["brand"] == "#0F766E"
        assert p["site"]["theme"]["brand_color"] == "#0F766E" and p["layout"]["tokens"]["heading_font"] == "serif"
        await ca.patch(f"/api/v1/cms/pages/{promo_page['id']}", json={"draft": {"blocks": [{"type": "text", "text": "Landing"}], "layout": {"header": "none"}}})
        await ca.post(f"/api/v1/cms/pages/{promo_page['id']}/submit")
        await cb.post(f"/api/v1/cms/pages/{promo_page['id']}/approve", json={"ok": True})
        await cb.post(f"/api/v1/cms/pages/{promo_page['id']}/publish", json={})
        q = await live("/promotions")
        assert q["layout"]["header"] == [] and q["layout"]["footer"]
        assert (await ca.patch(f"/api/v1/cms/pages/{home['id']}", json={"draft": {"blocks": [], "layout": {"header": "Bad Key"}}})).status_code == 422

        # approved brand tokens + brand context + read-only e-mail theme
        t = (await ca.patch(f"{base}/components/{theme['id']}", json={"draft": {"tokens": {"colors": {"brand": "red"}}}}))
        assert t.status_code == 422
        t = (await ca.patch(f"{base}/components/{theme['id']}", json={"draft": {"tokens": {"logo_asset_ref": "NOT-APPROVED-ASSET"}}}))
        assert t.status_code == 422 and "brand asset" in t.text
        info = (await ca.get(f"{base}/sites/{sid}/brand")).json()
        assert info["brand"] and info["tokens"]["colors"]["brand"] == "#0F766E" and info["email_theme"]["brand_color"] == "#0F766E"
        assert set(info["email_theme"]) == set(info["email_default_theme"])

        # page template: create a new page from a published template
        tpl = (await ca.post(f"{base}/sites/{sid}/components", json={"preset": "landing-basic", "key": "landing"})).json()
        assert (await ca.post(f"{base}/pages/from-template", json={"site_id": sid, "template_key": "landing", "title": "Early"})).status_code == 404
        await _publish(ca, cb, tpl["id"])
        np = await ca.post(f"{base}/pages/from-template", json={"site_id": sid, "template_key": "landing", "title": "Cleaning range"})
        assert np.status_code == 201, np.text
        d = (await ca.get(f"/api/v1/cms/pages/{np.json()['id']}")).json()
        assert d["status"] == "DRAFT" and d["draft"]["blocks"][0]["type"] == "section"
