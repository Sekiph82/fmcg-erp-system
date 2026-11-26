"""M46.S01.T001–T006 Content & Digital Experience Hub (unit + DB; the DB part needs M46_DB=1).

Real sessions and HTTP through the app: staff routes with logged-in personas (author / approver), public routes
without a login, portal members with the portal realm cookie. Synthetic POVU data only.
"""
import os
import uuid

import httpx
import pytest

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
PW = uuid.uuid4().hex + "Aa1!"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


# ── unit ──────────────────────────────────────────────────────────────────────

def test_block_validation_refuses_unsafe_links():
    from app.services import cms_service as cms
    doc, warnings = cms.validate_doc({"blocks": [{"type": "text", "text": "<script>alert(1)</script> see [POVU](/products)"},
                                                 {"type": "image", "url": "https://cdn.povu.example.com/a.png"}]})
    assert doc["blocks"][0]["text"].startswith("<script>")       # stored as text; rendered escaped, never as HTML
    assert warnings == ["An image has no alternative text."]
    for bad in ({"type": "button", "label": "x", "href": "javascript:alert(1)"},
                {"type": "button", "label": "x", "href": "//evil.example.com"},
                {"type": "image", "url": "http://cdn.povu.example.com/a.png", "alt": "a"},
                {"type": "text", "text": "[click](javascript:alert(1))"},
                {"type": "html", "html": "<b>x</b>"}):
        with pytest.raises(cms.CmsError):
            cms.validate_doc({"blocks": [bad]})


def test_personalize_slots_and_fallback():
    from app.services.cms_personalize import Visitor, personalize
    blocks = [{"type": "text", "id": "w", "slot": "hi", "text": "Welcome back", "audience": {"known": True, "lifecycle": ["CUSTOMER"]}},
              {"type": "text", "id": "f", "slot": "hi", "text": "Hello", "fallback": True},
              {"type": "text", "id": "sw", "text": "Karibu", "audience": {"locale": ["sw"]}}]
    anon = [b["id"] for b in personalize(blocks, Visitor(locale="en"))]
    known = [b["id"] for b in personalize(blocks, Visitor(vh="x", known=True, lifecycle="customer", locale="sw"))]
    lead = [b["id"] for b in personalize(blocks, Visitor(vh="x", known=True, lifecycle="LEAD", locale="en"))]
    assert anon == ["f"] and known == ["w", "sw"] and lead == ["f"]


def test_studio_review_flags_claims_and_terms():
    from types import SimpleNamespace
    from app.services import content_studio_service as cs
    prof = SimpleNamespace(terminology={"washpowder": "washing powder"}, banned_terms=["miracle"], claim_terms=["healthy"],
                           evidence=[{"id": "e1", "text": "POVU AllClean is made in Kenya", "source": "QA file"}])
    text, f = cs.review(prof, "POVU washpowder is a miracle. It is 50% better. It is healthy [E:e1]. Fake fact [E:e9].", "web")
    codes = [x["code"] for x in f]
    assert "washing powder" in text and "terminology" in codes and "banned_term" in codes
    assert codes.count("uncited_claim") == 1 and "unknown_evidence" in codes
    _, f2 = cs.review(prof, "x" * 300, "social")
    assert any(x["code"] == "too_long" for x in f2)


# ── helpers ───────────────────────────────────────────────────────────────────

async def _user(db, perms: tuple, tag: str):
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.models.role import Permission, Role
    from app.models.user import User
    u = User(username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test", full_name=tag.title(),
             hashed_password=hash_password(PW), is_active=True)
    role = Role(name=f"{tag}-{uuid.uuid4().hex[:6]}", is_active=True)
    for code in perms:
        p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
        if p is None:
            p = Permission(code=code, name=code, module=code.split(".")[0], action=code.split(".")[1], is_active=True)
            db.add(p)
            await db.flush()
        role.permissions.append(p)
    u.roles.append(role)
    db.add_all([role, u])
    return u.username


async def _people():
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        a = await _user(db, ("marketing.view", "marketing.create", "marketing.edit"), "author")
        b = await _user(db, ("marketing.view", "marketing.approve"), "approver")
        r = await _user(db, ("sales.view",), "outsider")
        await db.commit()
    return a, b, r


async def _login(c, username):
    r = await c.post("/api/v1/auth/login", data={"username": username, "password": PW})
    assert r.status_code == 200, r.text


async def _publish(cb, pid):
    """Approver publishes a page the author already submitted."""
    assert (await cb.post(f"/api/v1/cms/pages/{pid}/approve", json={"ok": True})).status_code == 200
    r = await cb.post(f"/api/v1/cms/pages/{pid}/publish", json={"note": "ok"})
    assert r.status_code == 200, r.text
    return r.json()


# ── T001/T002/T005: CMS, blog, SEO, multilingual ──────────────────────────────

@DB
@pytest.mark.asyncio
async def test_cms_staging_approval_publish_rollback_seo():
    a, b, r = await _people()
    key = f"povu{uuid.uuid4().hex[:5]}"
    async with _client() as ca, _client() as cb, _client() as cr, _client() as pub:
        await _login(ca, a)
        await _login(cb, b)
        await _login(cr, r)
        assert (await cr.get("/api/v1/cms/sites")).status_code == 403                       # no marketing permission
        assert (await ca.post("/api/v1/cms/sites", json={"name": "POVU", "key": key})).status_code == 403   # author cannot create sites
        site = (await cb.post("/api/v1/cms/sites", json={"name": "POVU Home Care", "key": key, "locales": ["en", "sw", "tr"],
                                                         "domain": "www.povu.example.com", "nav": [{"label": "Home", "path": "/"}]})).json()
        assert site["domain_status"] == "DNS_PENDING" and site["local_url"] == f"/site/{key}"
        sid = site["id"]
        bad = await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "Bad", "draft": {"blocks": [{"type": "button", "label": "x", "href": "javascript:alert(1)"}]}})
        assert bad.status_code == 422
        for junk in ({"blocks": ["x"]}, {"blocks": [{"type": "heading", "level": "abc", "text": "x"}]}, {"blocks": [{"type": "embed", "page_id": "nope"}]}):
            assert (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "Junk", "draft": junk})).status_code == 422   # (review #15)
        home = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "POVU home", "slug": "home", "draft": {
            "blocks": [{"type": "hero", "title": "POVU AllClean 1 L", "subtitle": "<img src=x onerror=alert(1)>"},
                       {"type": "text", "text": "Version one text"}],
            "seo": {"meta_title": "POVU AllClean — fresh clean", "meta_description": "short"}}})).json()
        assert home["path"] == "/" and home["status"] == "DRAFT"
        hid = home["id"]
        assert (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/"})).status_code == 404     # draft is not public
        assert (await ca.post(f"/api/v1/cms/pages/{hid}/publish", json={})).status_code == 403                    # author cannot publish
        assert (await cb.post(f"/api/v1/cms/pages/{hid}/publish", json={})).status_code == 422                    # review first
        assert (await ca.post(f"/api/v1/cms/pages/{hid}/submit")).status_code == 200
        v1 = await _publish(cb, hid)
        assert v1["version"] == 1 and v1["status"] == "PUBLISHED"
        p = await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/"})
        assert p.status_code == 200 and p.headers["cache-control"] == "public, max-age=60"
        body = p.json()
        assert "<img" not in p.text and body["page"]["version"] == 1      # markup stripped at input; the rest is plain text

        # staging: edits do not touch the live page until the next publish
        await ca.patch(f"/api/v1/cms/pages/{hid}", json={"draft": {"blocks": [{"type": "hero", "title": "POVU AllClean"}, {"type": "text", "text": "Version two text"}]}})
        live = (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/"})).json()
        assert live["blocks"][1]["text"] == "Version one text"
        prev = (await ca.get(f"/api/v1/cms/pages/{hid}/preview")).json()
        assert prev["preview"] and prev["blocks"][1]["text"] == "Version two text"
        await ca.post(f"/api/v1/cms/pages/{hid}/submit")
        assert (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/"})).status_code == 200   # in review: still live
        assert (await ca.post(f"/api/v1/cms/pages/{hid}/approve", json={"ok": True})).status_code == 403        # no approve permission
        assert (await cb.post(f"/api/v1/cms/pages/{hid}/approve", json={"ok": True})).status_code == 200
        await ca.patch(f"/api/v1/cms/pages/{hid}", json={"title": "POVU home (edited after approval)"})          # (review #5)
        assert (await cb.post(f"/api/v1/cms/pages/{hid}/publish", json={})).status_code == 422                    # needs a new review
        await ca.patch(f"/api/v1/cms/pages/{hid}", json={"title": "POVU home"})
        await ca.post(f"/api/v1/cms/pages/{hid}/submit")
        await _publish(cb, hid)
        assert (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/"})).json()["blocks"][1]["text"] == "Version two text"
        rb = await cb.post(f"/api/v1/cms/pages/{hid}/rollback", json={"version": 1})
        assert rb.status_code == 200 and rb.json()["version"] == 3
        assert (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/"})).json()["blocks"][1]["text"] == "Version one text"
        detail = (await ca.get(f"/api/v1/cms/pages/{hid}")).json()
        assert [v["version"] for v in detail["versions"]] == [3, 2, 1] and detail["versions"][0]["live"]

        # site tree, slug change → automatic redirect; loops refused
        about = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "About POVU", "slug": "about",
                                                          "draft": {"blocks": [{"type": "heading", "level": 1, "text": "About"}]}})).json()
        team = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "Team", "slug": "team", "parent_id": about["id"],
                                                         "draft": {"blocks": [{"type": "text", "text": "Our team"}]}})).json()
        assert team["path"] == "/about/team"
        for pid in (about["id"], team["id"]):
            await ca.post(f"/api/v1/cms/pages/{pid}/submit")
            await _publish(cb, pid)
        moved = (await ca.patch(f"/api/v1/cms/pages/{about['id']}", json={"slug": "company"})).json()
        assert moved["path"] == "/company" and moved["live_path"] == "/about"
        assert (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/about"})).status_code == 200    # (review #4c) moves on publish
        assert (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/company"})).status_code == 404
        assert (await ca.get(f"/api/v1/cms/pages/{team['id']}")).json()["path"] == "/company/team"     # children follow
        for pid in (about["id"], team["id"]):
            await ca.post(f"/api/v1/cms/pages/{pid}/submit")
            await _publish(cb, pid)
        red = (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/about/team"})).json()
        assert red == {"redirect": "/company/team", "code": 301}
        assert (await ca.post(f"/api/v1/cms/sites/{sid}/redirects", json={"from_path": "/x", "to_path": "/company"})).status_code == 403   # approver only
        assert (await cb.post(f"/api/v1/cms/sites/{sid}/redirects", json={"from_path": "/company/team", "to_path": "/about/team"})).status_code == 422
        assert (await cb.post(f"/api/v1/cms/sites/{sid}/redirects", json={"from_path": "/go", "to_path": "https://evil.example.com"})).status_code == 422
        await cb.post(f"/api/v1/cms/sites/{sid}/redirects", json={"from_path": "/company", "to_path": "/"})                 # a live page wins
        assert "redirect" not in (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/company"})).json()
        assert (await ca.patch(f"/api/v1/cms/pages/{about['id']}", json={"parent_id": team["id"]})).status_code == 422   # no cycles

        # CTA, embed, dynamic table page
        assert (await ca.post(f"/api/v1/cms/sites/{sid}/ctas", json={"key": "find-a-shop", "label": "x", "href": "/company"})).status_code == 403
        await cb.post(f"/api/v1/cms/sites/{sid}/ctas", json={"key": "find-a-shop", "label": "Find a shop", "href": "/company"})
        tbl = (await ca.post(f"/api/v1/cms/sites/{sid}/tables", json={"key": "products", "name": "Products",
                                                                     "columns": [{"key": "name", "label": "Name"}, {"key": "size", "label": "Size"}]})).json()
        assert (await ca.put(f"/api/v1/cms/tables/{tbl['id']}/rows", json={"rows": [{"slug": "povu-allclean-1l", "name": "POVU AllClean", "size": "1 L"},
                                                                                  {"slug": "povu-whitecare-1kg", "name": "POVU WhiteCare", "size": "1 kg"}]})).json() == {"saved": 2}
        assert (await ca.patch(f"/api/v1/cms/tables/{tbl['id']}", json={"published": True})).status_code == 403   # publishing data = approver
        assert (await cb.patch(f"/api/v1/cms/tables/{tbl['id']}", json={"published": True})).status_code == 200
        assert (await ca.put(f"/api/v1/cms/tables/{tbl['id']}/rows", json={"rows": [{"slug": "x", "name": "x"}]})).status_code == 403   # live rows: approver
        assert (await cb.put(f"/api/v1/cms/tables/{tbl['id']}/rows", json={"rows": [{"slug": "d", "name": "a"}, {"slug": "d", "name": "b"}]})).status_code == 422
        prod = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "Products", "slug": "products", "kind": "DYNAMIC",
                                                         "table_id": tbl["id"], "draft": {"blocks": [
                                                             {"type": "heading", "level": 1, "text": "{{row.name}}"}, {"type": "text", "text": "Size: {{row.size}}"},
                                                             {"type": "cta", "cta_key": "find-a-shop"}, {"type": "embed", "page_id": team["id"]},
                                                             {"type": "table", "table_key": "products"}]}})).json()
        await ca.post(f"/api/v1/cms/pages/{prod['id']}/submit")
        await _publish(cb, prod["id"])
        dp = (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/products/povu-allclean-1l"})).json()
        assert dp["page"]["title"] == "POVU AllClean" and dp["blocks"][1]["text"] == "Size: 1 L"
        assert dp["blocks"][2]["cta"]["href"] == "/company" and dp["blocks"][3]["blocks"][0]["text"] == "Our team"
        assert [x["slug"] for x in dp["blocks"][4]["rows"]] == ["povu-allclean-1l", "povu-whitecare-1kg"]      # row order as entered
        assert (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/products/nope"})).status_code == 404
        await pub.post(f"/api/v1/public/cms/site/{key}/cta/find-a-shop/click")
        cta = (await ca.get(f"/api/v1/cms/sites/{sid}/ctas")).json()[0]
        assert cta["views"] == 1 and cta["clicks"] == 1

        # blog + SEO/AEO audits
        post = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "How to store POVU AllClean", "slug": "store-allclean", "kind": "POST",
                                                         "author": "POVU QA", "category": "Guides", "draft": {
                                                             "blocks": [{"type": "heading", "level": 1, "text": "How do I store POVU AllClean?"},
                                                                        {"type": "text", "text": "Keep it cool. See [our team](/company/team) and [old](/missing)."},
                                                                        {"type": "faq", "items": [{"q": "How long does it keep?", "a": "Twelve months unopened."}]}],
                                                             "seo": {"meta_title": "How to store POVU AllClean", "keywords": ["storage"]}}})).json()
        assert post["path"] == "/blog/store-allclean"
        audit = (await ca.get(f"/api/v1/cms/pages/{post['id']}/seo-audit")).json()
        codes = {f["code"] for f in audit["findings"]}
        assert {"no_description", "broken_link", "thin", "keyword_missing"} <= codes and audit["search_console"]["status"] == "NOT_CONFIGURED"
        assert "/missing" in str(audit["findings"]) and "/company/team" not in str([f for f in audit["findings"] if f["code"] == "broken_link"])
        aeo = (await ca.get(f"/api/v1/cms/pages/{post['id']}/aeo-audit")).json()
        assert aeo["visibility"]["status"] == "NOT_AVAILABLE" and {c["code"]: c["ok"] for c in aeo["checks"]}["faq_schema"]
        await ca.post(f"/api/v1/cms/pages/{post['id']}/submit")
        await _publish(cb, post["id"])
        bl = (await pub.get(f"/api/v1/public/cms/site/{key}/blog")).json()
        assert [x["path"] for x in bl["posts"]] == ["/blog/store-allclean"] and bl["posts"][0]["author"] == "POVU QA"
        pp = (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/blog/store-allclean"})).json()
        types = [x["@type"] for x in pp["json_ld"]]
        assert types == ["BlogPosting", "FAQPage"] and pp["page"]["author"] == "POVU QA"

        # multilingual: translation workflow, hreflang, fallback
        tr = await ca.post(f"/api/v1/cms/pages/{hid}/translate", json={"locale": "sw"})
        assert tr.status_code == 201 and tr.json()["translation_state"] == "NEEDS_REVIEW"
        sw = tr.json()["id"]
        assert (await ca.post(f"/api/v1/cms/pages/{hid}/translate", json={"locale": "sw"})).status_code == 409
        await ca.patch(f"/api/v1/cms/pages/{sw}", json={"title": "POVU nyumbani", "draft": {"blocks": [{"type": "hero", "title": "Maji ya POVU"}]}})
        await ca.post(f"/api/v1/cms/pages/{sw}/translation-state", json={"state": "REVIEWED"})
        await ca.post(f"/api/v1/cms/pages/{sw}/submit")
        await _publish(cb, sw)
        swp = (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/", "locale": "sw"})).json()
        assert swp["blocks"][0]["title"] == "Maji ya POVU" and {x["locale"] for x in swp["alternates"]} == {"en", "sw"}
        trp = (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/", "locale": "tr"})).json()
        assert trp["page"]["locale"] == "en"                                                   # no Turkish page yet: default locale
        await ca.post(f"/api/v1/cms/pages/{hid}/submit")
        await _publish(cb, hid)
        assert (await ca.get(f"/api/v1/cms/pages/{sw}")).json()["translation_state"] == "STALE"   # source changed after review
        sm = (await pub.get(f"/api/v1/public/cms/site/{key}/sitemap.xml")).text
        assert f"/site/{key}/en</loc>" in sm and 'hreflang="sw"' in sm and "/products/povu-whitecare-1kg" in sm and "/blog/store-allclean" in sm
        rb_txt = (await pub.get(f"/api/v1/public/cms/site/{key}/robots.txt")).text
        assert "Sitemap:" in rb_txt and f"/public/cms/site/{key}/sitemap.xml" in rb_txt

        # unpublish → gone
        assert (await cb.post(f"/api/v1/cms/pages/{post['id']}/unpublish")).status_code == 200
        assert (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/blog/store-allclean"})).status_code == 404


# ── T004 personalization + experiments ───────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_personalization_consent_cache_and_bandit():
    from app.db.session import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.crm import CRMContact
    from app.models.portal import PortalAccount, PortalAccountStatus, PortalAccountType, PortalUser, PortalUserRole
    from app.services import web_analytics_service as wa
    a, b, _ = await _people()
    key = f"pz{uuid.uuid4().hex[:5]}"
    email = f"mama-{uuid.uuid4().hex[:5]}@example.com"
    async with AsyncSessionLocal() as db:
        db.add(CRMContact(full_name="Mama Duka", email=email, lifecycle_stage="CUSTOMER"))
        acct = PortalAccount(account_code=f"PZ-{uuid.uuid4().hex[:6]}", account_type=PortalAccountType.CUSTOMER, portal_status=PortalAccountStatus.ACTIVE)
        db.add(acct)
        await db.flush()
        db.add(PortalUser(portal_account_id=acct.id, full_name="Mama Duka", email=email, password_hash=hash_password(PW),
                          role_type=PortalUserRole.OWNER, is_active=True))
        await wa.record_consent(db, "visitor-known-1", True, True)
        await db.flush()
        assert await wa.identify(db, "visitor-known-1", email)
        await wa.record_consent(db, "visitor-anon-01", True, False)
        await db.commit()
    async with _client() as ca, _client() as cb, _client() as pub, _client() as member:
        await _login(ca, a)
        await _login(cb, b)
        assert (await member.post("/api/v1/portal-self/auth/login", json={"email": email, "password": PW})).status_code == 200
        sid = (await cb.post("/api/v1/cms/sites", json={"name": "POVU PZ", "key": key})).json()["id"]
        pg = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "Offers", "slug": "offers", "draft": {"blocks": [
            {"type": "text", "id": "w", "slot": "hi", "text": "Welcome back, valued customer", "audience": {"known": True, "lifecycle": ["CUSTOMER"]}},
            {"type": "text", "id": "f", "slot": "hi", "text": "Hello, new visitor", "fallback": True},
            {"type": "button", "id": "ba", "label": "Order now", "href": "/order", "experiment": {"key": "cta", "variant": "a"}},
            {"type": "button", "id": "bb", "label": "See prices", "href": "/prices", "experiment": {"key": "cta", "variant": "b"}}]}})).json()
        await ca.post(f"/api/v1/cms/pages/{pg['id']}/submit")
        await _publish(cb, pg["id"])
        url = f"/api/v1/public/cms/site/{key}/page"
        # (review #7) a self-typed e-mail is not verified: no CRM data is used for it
        selfid = (await pub.get(url, params={"path": "/offers", "visitor": "visitor-known-1"})).json()
        assert selfid["personalized"] and selfid["blocks"][0]["id"] == "f"
        known = await member.get(url, params={"path": "/offers", "visitor": "visitor-known-1"})   # signed-in portal user: verified
        kj = known.json()
        assert known.headers["cache-control"] == "private, no-store" and kj["personalized"]
        assert [x["id"] for x in kj["blocks"]][0] == "w" and email not in known.text and "Mama" not in known.text
        assert "audience" not in known.text and "CUSTOMER" not in known.text and "fallback" not in known.text     # (review #9)
        anon = await pub.get(url, params={"path": "/offers"})
        assert anon.headers["cache-control"] == "public, max-age=60" and [x["id"] for x in anon.json()["blocks"]] == ["f", "ba"]   # control
        # withdrawn marketing consent → anonymous fallback immediately
        async with AsyncSessionLocal() as db:
            await wa.record_consent(db, "visitor-known-1", True, False)
            await db.commit()
        assert (await pub.get(url, params={"path": "/offers", "visitor": "visitor-known-1"})).json()["personalized"] is False
        # A/B: sticky per visitor; views recorded only with analytics consent
        first = (await pub.get(url, params={"path": "/offers", "visitor": "visitor-anon-01"})).json()["experiments"]["cta"]
        for _ in range(3):
            assert (await pub.get(url, params={"path": "/offers", "visitor": "visitor-anon-01"})).json()["experiments"]["cta"] == first
        await pub.get(url, params={"path": "/offers", "visitor": "no-consent-visitor"})
        exp = (await ca.get(f"/api/v1/cms/pages/{pg['id']}/experiments")).json()[0]
        assert exp["views"] == 2                          # known-1 and anon-01 (analytics-consented); no-consent not counted
        assert (await pub.post(f"/api/v1/public/cms/site/{key}/convert", json={"path": "/offers", "experiment": "cta", "visitor": "visitor-anon-01"})).json() == {"recorded": True}
        assert (await pub.post(f"/api/v1/public/cms/site/{key}/convert", json={"path": "/offers", "experiment": "cta", "visitor": "visitor-anon-01"})).json() == {"recorded": False}
        assert (await pub.post(f"/api/v1/public/cms/site/{key}/convert", json={"path": "/offers", "experiment": "cta", "visitor": "no-consent-visitor"})).json() == {"recorded": False}
        # bandit: converting variant gets more traffic
        assert (await ca.patch(f"/api/v1/cms/experiments/{exp['id']}", json={"mode": "BANDIT"})).status_code == 403
        await cb.patch(f"/api/v1/cms/experiments/{exp['id']}", json={"mode": "BANDIT"})
        async with AsyncSessionLocal() as db:
            from app.models.cms import CmsExperiment
            e = await db.get(CmsExperiment, uuid.UUID(exp["id"]))
            e.counts = {"a": {"n": 200, "c": 60}, "b": {"n": 200, "c": 4}}
            await db.commit()
        seen = {"a": 0, "b": 0}
        for i in range(30):
            vis = f"bandit-visitor-{i:03d}"
            async with AsyncSessionLocal() as db:
                await wa.record_consent(db, vis, True, False)
                await db.commit()
            seen[(await pub.get(url, params={"path": "/offers", "visitor": vis})).json()["experiments"]["cta"]] += 1
        assert seen["a"] >= 25
        st = (await ca.get(f"/api/v1/cms/pages/{pg['id']}/experiments")).json()[0]
        assert st["mode"] == "BANDIT" and next(v for v in st["variants"] if v["variant"] == "a")["p_best"] > 0.95
        # forgetting a visitor removes their experiment attribution
        async with AsyncSessionLocal() as db:
            await wa.forget(db, "visitor-anon-01")
            await db.commit()
            from sqlalchemy import func, select
            from app.models.cms import CmsExperimentEvent
            assert (await db.execute(select(func.count()).select_from(CmsExperimentEvent).where(
                CmsExperimentEvent.visitor_hash == wa.hashed("v", "visitor-anon-01")))).scalar_one() == 0


# ── T006 memberships, media, KB access groups ────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_members_media_captions_timeline_kb(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.core.security import hash_password
    from app.db.session import AsyncSessionLocal
    from app.models.knowledge_base import KBArticle
    from app.models.portal import PortalAccount, PortalAccountStatus, PortalAccountType, PortalUser, PortalUserRole
    from app.models.sales import Customer
    monkeypatch.setattr(settings, "MEDIA_STORAGE_PATH", str(tmp_path))
    a, b, _ = await _people()
    s = uuid.uuid4().hex[:5]
    async with AsyncSessionLocal() as db:
        cust = Customer(code=f"MB-{s}", name="POVU Member Outlet", currency="KES")
        db.add(cust)
        await db.flush()
        acc = {}
        for k, typ in (("in", PortalAccountType.CUSTOMER), ("out", PortalAccountType.CUSTOMER)):
            acc[k] = PortalAccount(account_code=f"MB-{k}-{s}", account_type=typ, portal_status=PortalAccountStatus.ACTIVE,
                                   linked_customer_id=str(cust.id) if k == "in" else None)
            db.add(acc[k])
            await db.flush()
            db.add(PortalUser(portal_account_id=acc[k].id, full_name=f"Member {k}", email=f"m-{k}-{s}@example.com",
                              password_hash=hash_password(PW), role_type=PortalUserRole.OWNER, is_active=True))
        await db.commit()
        ids = {k: str(v.id) for k, v in acc.items()}
        cid = cust.id
    key = f"mb{s}"
    async with _client() as ca, _client() as cb, _client() as anon, _client() as m_in, _client() as m_out:
        await _login(ca, a)
        await _login(cb, b)
        for c, k in ((m_in, "in"), (m_out, "out")):
            assert (await c.post("/api/v1/portal-self/auth/login", json={"email": f"m-{k}-{s}@example.com", "password": PW})).status_code == 200
        assert (await ca.post("/api/v1/cms/access-lists", json={"name": "x", "account_ids": [ids["in"]]})).status_code == 403
        acl = (await cb.post("/api/v1/cms/access-lists", json={"name": f"Gold members {s}", "account_ids": [ids["in"]]})).json()
        assert (await cb.post("/api/v1/cms/access-lists", json={"name": "bad", "account_ids": [str(uuid.uuid4())]})).status_code == 422
        sid = (await cb.post("/api/v1/cms/sites", json={"name": "POVU Members", "key": key})).json()["id"]
        pg = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "Members price list", "slug": "members",
                                                       "draft": {"blocks": [{"type": "text", "text": "Secret distributor prices"}]}})).json()
        assert (await ca.patch(f"/api/v1/cms/pages/{pg['id']}", json={"access": "MEMBERS", "access_list_id": acl["id"]})).status_code == 403
        assert (await cb.patch(f"/api/v1/cms/pages/{pg['id']}", json={"access": "MEMBERS", "access_list_id": acl["id"]})).status_code == 200
        await ca.post(f"/api/v1/cms/pages/{pg['id']}/submit")
        await _publish(cb, pg["id"])
        url = f"/api/v1/public/cms/site/{key}/page"
        r0 = await anon.get(url, params={"path": "/members"})
        assert r0.status_code == 401 and "Secret" not in r0.text
        assert (await m_out.get(url, params={"path": "/members"})).status_code == 403
        ok = await m_in.get(url, params={"path": "/members"})
        assert ok.status_code == 200 and ok.headers["cache-control"] == "private, no-store" and ok.json()["seo"]["noindex"]
        assert "/members" not in (await anon.get(f"/api/v1/public/cms/site/{key}/sitemap.xml")).text
        await cb.patch(f"/api/v1/cms/access-lists/{acl['id']}", json={"revoked_ids": [ids["in"]]})
        assert (await m_in.get(url, params={"path": "/members"})).status_code == 403            # revoked
        await cb.patch(f"/api/v1/cms/access-lists/{acl['id']}", json={"revoked_ids": []})

        # media: content sniffing, captions, gated playback with range, views on the timeline
        mp4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 4096
        bad = await ca.post("/api/v1/cms/media", data={"title": "fake"}, files={"file": ("clip.mp4", b"\x89PNG\r\n\x1a\n" + b"0" * 100, "video/mp4")})
        assert bad.status_code == 422
        assert (await ca.post("/api/v1/cms/media", data={"title": "x", "access_list_id": acl["id"]},
                              files={"file": ("a.mp4", mp4, "video/mp4")})).status_code == 403          # gating is an approver decision
        med = (await cb.post("/api/v1/cms/media", data={"title": "How to stack POVU crates", "access_list_id": acl["id"]},
                             files={"file": ("crates.mp4", mp4, "video/mp4")})).json()
        assert med["kind"] == "VIDEO" and med["mime"] == "video/mp4"
        mid = med["id"]
        assert (await cb.put(f"/api/v1/cms/media/{mid}/captions/sw", json={"vtt": "not vtt"})).status_code == 422
        vtt = "WEBVTT\n\n00:00.000 --> 00:02.000\n<script>x</script>Panga kreti za POVU\n"
        assert (await ca.put(f"/api/v1/cms/media/{mid}/captions/sw", json={"vtt": vtt})).status_code == 403   # gated media: approver
        assert (await cb.put(f"/api/v1/cms/media/{mid}/captions/sw", json={"vtt": vtt})).json()["captions"] == ["sw"]
        assert (await anon.get(f"/api/v1/public/cms/media/{mid}/file")).status_code == 401
        assert (await m_out.get(f"/api/v1/public/cms/media/{mid}/file")).status_code == 403
        part = await m_in.get(f"/api/v1/public/cms/media/{mid}/file", headers={"Range": "bytes=0-15"})
        assert part.status_code == 206 and part.content == mp4[:16]
        cap = await m_in.get(f"/api/v1/public/cms/media/{mid}/captions/sw")
        assert cap.headers["content-type"].startswith("text/vtt") and "<script>" not in cap.text and "Panga kreti" in cap.text
        assert (await m_in.post(f"/api/v1/public/cms/media/{mid}/view", json={"seconds": 12})).json() == {"recorded": True}
        assert (await m_in.post(f"/api/v1/public/cms/media/{mid}/view", json={"seconds": 40})).json() == {"recorded": False}
        views = (await ca.get(f"/api/v1/cms/media/{mid}/views")).json()
        assert len(views) == 1 and views[0]["seconds"] == 40 and views[0]["member"]
        async with AsyncSessionLocal() as db:
            from app.services.customer_timeline_service import timeline
            from types import SimpleNamespace
            boss = SimpleNamespace(id=None, username="admin", is_superuser=True, roles=[], access_scopes=[])
            tl = await timeline(db, cid, boss)
            assert any(i["type"] == "media_view" for i in tl["events"])
        # public podcast feed lists public audio only
        wav = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 64
        ep = (await cb.post("/api/v1/cms/media", data={"title": "POVU podcast ep 1", "podcast": f"POVU Talk {s}", "public": "true"},
                            files={"file": ("ep1.wav", wav, "audio/wav")})).json()
        feed = await anon.get(f"/api/v1/public/cms/podcast/POVU Talk {s}.xml")
        assert feed.status_code == 200 and ep["id"] in feed.text

        # (review #3) rows of a table behind a members-only dynamic page never show on a public page
        tb = (await ca.post(f"/api/v1/cms/sites/{sid}/tables", json={"key": "member_prices", "name": "Member prices",
                                                                    "columns": [{"key": "name"}, {"key": "price"}]})).json()
        await ca.put(f"/api/v1/cms/tables/{tb['id']}/rows", json={"rows": [{"slug": "allclean", "name": "POVU AllClean", "price": "42"}]})
        await cb.patch(f"/api/v1/cms/tables/{tb['id']}", json={"published": True})
        dyn = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "Member price", "slug": "member-price", "kind": "DYNAMIC",
                                                        "table_id": tb["id"], "draft": {"blocks": [{"type": "text", "text": "{{row.price}}"}]}})).json()
        await cb.patch(f"/api/v1/cms/pages/{dyn['id']}", json={"access": "MEMBERS", "access_list_id": acl["id"]})
        pubpg = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "Open", "slug": "open",
                                                          "draft": {"blocks": [{"type": "table", "table_key": "member_prices"}]}})).json()
        for pid in (dyn["id"], pubpg["id"]):
            await ca.post(f"/api/v1/cms/pages/{pid}/submit")
            await _publish(cb, pid)
        op = await anon.get(url, params={"path": "/open"})
        assert op.status_code == 200 and op.json()["blocks"][0]["rows"] == [] and '"42"' not in op.text   # the quoted price value; ids may contain 42
        assert (await anon.get(url, params={"path": "/member-price/allclean"})).status_code == 401
        assert (await m_in.get(url, params={"path": "/member-price/allclean"})).json()["blocks"][0]["text"] == "42"

        # KB access groups
        async with AsyncSessionLocal() as db:
            db.add(KBArticle(slug=f"members-faq-{s}", title="Member FAQ", content_md="Distributor rebates", status="PUBLISHED",
                             is_internal_only=False, access_list_id=uuid.UUID(acl["id"])))
            await db.commit()
        assert (await anon.get(f"/api/v1/public/kb/articles/members-faq-{s}")).status_code == 404       # not in the public KB
        assert (await anon.get("/api/v1/public/kb/members/articles")).status_code == 401
        assert (await m_out.get(f"/api/v1/public/kb/members/articles/members-faq-{s}")).status_code == 404
        assert (await m_in.get(f"/api/v1/public/kb/members/articles/members-faq-{s}")).json()["content_md"] == "Distributor rebates"


# ── T003 content studio ──────────────────────────────────────────────────────

@DB
@pytest.mark.asyncio
async def test_studio_budget_fake_model_review_and_approval(monkeypatch):
    from app.services import ai_provider
    a, b, _ = await _people()
    calls = []

    class Fake:
        async def generate_text(self, prompt, system=None):
            calls.append(prompt)
            return ai_provider.AIResponse(text="POVU AllClean is made in Kenya [E:e1]. Order from your distributor.", provider="fake",
                                          model="fake-1", prompt_tokens=900, completion_tokens=100, latency_ms=1)
    monkeypatch.setattr(ai_provider, "get_ai_provider", lambda: Fake())
    async with _client() as ca, _client() as cb:
        await _login(ca, a)
        await _login(cb, b)
        assert (await ca.post("/api/v1/content-studio/profiles", json={"name": "POVU"})).status_code == 403
        prof = (await cb.post("/api/v1/content-studio/profiles", json={
            "name": f"POVU voice {uuid.uuid4().hex[:4]}", "voice": "Warm, plain, Kenyan English.", "banned_terms": ["miracle"],
            "terminology": {"washpowder": "washing powder"}, "claim_terms": ["healthy"], "monthly_budget": 0.03,
            "evidence": [{"id": "e1", "text": "POVU AllClean is made in Kenya", "source": "Plant QA register"}]})).json()
        assert (await cb.patch(f"/api/v1/content-studio/profiles/{prof['id']}", json={"asset_ids": [str(uuid.uuid4())]})).status_code == 422
        d1 = (await ca.post("/api/v1/content-studio/drafts", json={"profile_id": prof["id"], "channel": "web", "template": "product_launch",
                                                                   "brief": "Launch POVU AllClean 1 L", "evidence_ids": ["e1"]})).json()
        assert d1["engine"] == "fake" and d1["cost"] > 0 and not [f for f in d1["findings"] if f["level"] == "error"]
        d2 = (await ca.post("/api/v1/content-studio/drafts", json={"profile_id": prof["id"], "channel": "web", "template": "product_launch",
                                                                   "brief": "Launch POVU WhiteCare 1 kg", "evidence_ids": ["e1"]})).json()
        d3 = (await ca.post("/api/v1/content-studio/drafts", json={"profile_id": prof["id"], "channel": "sms", "template": "promotion",
                                                                   "brief": "POVU washpowder promo this weekend"})).json()
        assert d2["engine"] == "fake" and d3["engine"] == "rules" and len(calls) == 2              # budget reached: deterministic
        assert "washing powder" in d3["body"] and len(d3["body"]) <= 160
        # an uncited claim blocks approval; the author cannot approve their own draft
        await ca.patch(f"/api/v1/content-studio/drafts/{d1['id']}", json={"body": "POVU is the healthiest miracle cleaner, 100% natural."})
        await ca.post(f"/api/v1/content-studio/drafts/{d1['id']}/submit")
        r = await cb.post(f"/api/v1/content-studio/drafts/{d1['id']}/decide", json={"ok": True})
        assert r.status_code == 422 and "error findings" in r.text
        assert (await cb.post(f"/api/v1/content-studio/drafts/{d1['id']}/decide", json={"ok": False, "note": "claims"})).json()["status"] == "REJECTED"
        await ca.post(f"/api/v1/content-studio/drafts/{d2['id']}/submit")
        assert (await ca.post(f"/api/v1/content-studio/drafts/{d2['id']}/decide", json={"ok": True})).status_code == 403
        ap = (await cb.post(f"/api/v1/content-studio/drafts/{d2['id']}/decide", json={"ok": True})).json()
        assert ap["status"] == "APPROVED" and [h["action"] for h in ap["history"]] == ["generated", "submitted", "approved"]
        # repurpose to another channel; using an approved draft only fills a CMS page draft
        rp = (await ca.post("/api/v1/content-studio/drafts", json={"profile_id": prof["id"], "channel": "social", "template": "announcement",
                                                                   "brief": "", "source_id": d2["id"]}))
        assert rp.status_code == 201 and rp.json()["source_id"] == d2["id"] and len(rp.json()["body"]) <= 280
        sid = (await cb.post("/api/v1/cms/sites", json={"name": "Studio site", "key": f"st{uuid.uuid4().hex[:5]}"})).json()["id"]
        pg = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "AllClean", "slug": "allclean"})).json()
        assert (await ca.post(f"/api/v1/content-studio/drafts/{d3['id']}/to-page", json={"page_id": pg["id"]})).status_code == 422
        assert (await ca.post(f"/api/v1/content-studio/drafts/{d2['id']}/to-page", json={"page_id": pg["id"]})).status_code == 200
        page = (await ca.get(f"/api/v1/cms/pages/{pg['id']}")).json()
        assert page["status"] == "DRAFT" and page["live_version"] is None and "[E:" not in str(page["draft"]["blocks"])
