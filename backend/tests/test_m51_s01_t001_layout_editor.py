"""M51.S01.T001 nested layout through the real staff and public APIs (DB-gated: M51_DB=1).

Personas log in over httpx ASGITransport; synthetic POVU data only.
"""
import os
import uuid

import httpx
import pytest

DB = pytest.mark.skipif(os.environ.get("M51_DB") != "1", reason="requires the task-owned disposable PostgreSQL")
PW = uuid.uuid4().hex + "Aa1!"


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M51_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def client():
    from app.api.v1.endpoints.cms_layout import router
    from app.main import app
    if not any(getattr(r, "path", "").startswith("/api/v1/cms-layout") for r in app.routes):
        app.include_router(router, prefix="/api/v1/cms-layout")      # until module_registry carries the route
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


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


async def people():
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        a = await _user(db, ("marketing.view", "marketing.create", "marketing.edit"), "author")
        b = await _user(db, ("marketing.view", "marketing.approve"), "approver")
        r = await _user(db, ("sales.view",), "outsider")
        await db.commit()
    return a, b, r


async def login(c, username):
    r = await c.post("/api/v1/auth/login", data={"username": username, "password": PW})
    assert r.status_code == 200, r.text


NESTED = {"blocks": [
    {"type": "section", "id": "intro", "as": "section", "label": "Introduction",
     "style": {"desktop": {"padding_top": "xl", "padding_bottom": "xl", "background": "surface"}, "mobile": {"padding_top": "md"}},
     "children": [{"type": "row", "id": "r1", "style": {"desktop": {"gap": "lg", "valign": "center"}}, "children": [
         {"type": "column", "id": "c1", "style": {"desktop": {"span": 7}}, "children": [
             {"type": "heading", "id": "h1", "level": 1, "text": "POVU AllClean 1 L", "style": {"desktop": {"font_size": "4xl", "color": "brand"}, "mobile": {"font_size": "2xl"}}},
             {"type": "text", "id": "t1", "text": "<script>alert(1)</script> Everyday home care."}]},
         {"type": "column", "id": "c2", "style": {"desktop": {"span": 5}}, "hide": ["mobile"], "children": [
             {"type": "product", "id": "p1", "name": "POVU AllClean 1 L", "size": "1 L"}]}]}]}]}


@DB
@pytest.mark.asyncio
async def test_nested_layout_edit_approve_publish_public_css_rollback():
    a, b, r = await people()
    key = f"povu{uuid.uuid4().hex[:5]}"
    async with client() as ca, client() as cb, client() as cr, client() as pub:
        await login(ca, a)
        await login(cb, b)
        await login(cr, r)
        assert (await cr.get("/api/v1/cms-layout/meta")).status_code == 403
        meta = (await ca.get("/api/v1/cms-layout/meta")).json()
        assert meta["breakpoints"] == ["desktop", "tablet", "mobile"] and "padding_top" in meta["style"]
        sid = (await cb.post("/api/v1/cms/sites", json={"name": "POVU Home Care", "key": key, "locales": ["en", "sw"]})).json()["id"]

        # unknown property / value / breakpoint and raw colour are refused at save, not stored
        for bad in ({"type": "text", "text": "x", "style": {"desktop": {"position": "fixed"}}}, {"type": "text", "text": "x", "style": {"desktop": {"color": "#FF0000"}}},
                    {"type": "text", "text": "x", "style": {"watch": {"color": "brand"}}}, {"type": "row", "children": [{"type": "text", "text": "x"}]}):
            assert (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "Bad", "draft": {"blocks": [bad]}})).status_code == 422
        page = (await ca.post("/api/v1/cms/pages", json={"site_id": sid, "title": "POVU landing", "slug": "home", "draft": NESTED})).json()
        pid = page["id"]
        draft = (await ca.get(f"/api/v1/cms/pages/{pid}")).json()["draft"]
        assert draft["blocks"][0]["children"][0]["children"][1]["hide"] == ["mobile"]

        # canvas preview of an unsaved document: validated, css generated per breakpoint, errors reported
        pv = await ca.post("/api/v1/cms-layout/preview", json={"site_id": sid, "doc": NESTED})
        assert pv.status_code == 200
        sec = pv.json()["blocks"][0]
        assert sec["css"]["desktop"]["paddingTop"] == 40 and sec["css"]["mobile"]["paddingTop"] == 16
        col = sec["children"][0]["children"][0]
        assert col["css"]["desktop"]["gridColumn"] == "span 7 / span 7" and col["css"]["mobile"]["gridColumn"] == "span 12 / span 12"
        assert (await ca.post("/api/v1/cms-layout/preview", json={"site_id": sid, "doc": {"blocks": [{"type": "text", "style": {"desktop": {"color": "red"}}}]}})).status_code == 422

        # publish needs a different approver
        assert (await ca.post(f"/api/v1/cms/pages/{pid}/submit")).status_code == 200
        assert (await cb.post(f"/api/v1/cms/pages/{pid}/approve", json={"ok": True})).status_code == 200
        assert (await cb.post(f"/api/v1/cms/pages/{pid}/publish", json={"note": "v1 layout"})).status_code == 200
        live = (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/"})).json()
        lsec = live["blocks"][0]
        assert lsec["type"] == "section" and lsec["css"]["desktop"]["backgroundColor"] == "#F3F4F6" and lsec["as"] == "section"
        h1 = lsec["children"][0]["children"][0]["children"][0]
        assert h1["css"]["desktop"]["color"] == "#1D4ED8" and h1["css"]["mobile"]["fontSize"] == "28px" and h1["css"]["tablet"]["fontSize"] == "48px"
        assert lsec["children"][0]["children"][1]["hide"] == ["mobile"]
        assert live["layout"]["header"] == [] and live["layout"]["tokens"]["colors"]["brand"] == "#1D4ED8"
        # the request sanitizer already stripped the markup; whatever text remains is data rendered escaped by React
        assert "<script" not in lsec["children"][0]["children"][0]["children"][1]["text"]
        import json as _json
        for blk in (lsec, h1):
            for props in blk["css"].values():
                assert all("<" not in str(v) and ";" not in str(v) for v in props.values())

        # edit → review → publish v2, then roll back to v1 (nested structure restored)
        v2 = _json.loads(_json.dumps(NESTED))
        v2["blocks"][0]["children"][0]["children"][0]["children"][0]["text"] = "POVU Hand Wash Powder 1 kg Pouch"
        assert (await ca.patch(f"/api/v1/cms/pages/{pid}", json={"draft": v2})).status_code == 200
        await ca.post(f"/api/v1/cms/pages/{pid}/submit")
        await cb.post(f"/api/v1/cms/pages/{pid}/approve", json={"ok": True})
        await cb.post(f"/api/v1/cms/pages/{pid}/publish", json={})
        assert (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/"})).json()["blocks"][0]["children"][0]["children"][0]["children"][0]["text"].endswith("Pouch")
        assert (await cb.post(f"/api/v1/cms/pages/{pid}/rollback", json={"version": 1})).status_code == 200
        back = (await pub.get(f"/api/v1/public/cms/site/{key}/page", params={"path": "/"})).json()["blocks"][0]["children"][0]["children"][0]["children"][0]
        assert back["text"] == "POVU AllClean 1 L"

        # the staff preview and the SEO audit see nested content too (one H1 found inside the section)
        sp = (await ca.get(f"/api/v1/cms/pages/{pid}/preview")).json()
        assert sp["blocks"][0]["css"]["desktop"]["paddingTop"] == 40
        audit = (await ca.get(f"/api/v1/cms/pages/{pid}/seo-audit")).json()
        assert not any(f["code"] == "h1" for f in audit["findings"])
