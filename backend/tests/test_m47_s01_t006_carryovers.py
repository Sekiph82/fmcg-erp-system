"""M47.S01.T006 M46 review carry-overs (DB part needs M46_DB=1).

Public write calls are rate limited per client address; sitemap and block expansion are bounded; experiment events
follow the analytics retention; the first experiment row is race-safe; the podcast feed has channel link/description;
oversized media uploads are refused from the declared length before the body is read.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def _client():
    from app.main import app
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test")


@DB
@pytest.mark.asyncio
async def test_public_writes_rate_limited(monkeypatch):
    from app.api.v1.endpoints import cms_public
    monkeypatch.setattr(cms_public, "WRITE_LIMIT", 3)
    cms_public._hits.clear()
    async with _client() as c:
        codes = [(await c.post("/api/v1/public/cms/site/no-such-site/cta/x/click")).status_code for _ in range(4)]
    assert codes == [404, 404, 404, 429]
    cms_public._hits.clear()


@DB
@pytest.mark.asyncio
async def test_bounds_retention_race_and_feed(monkeypatch, tmp_path):
    from sqlalchemy import func, select
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.cms import CmsCta, CmsExperiment, CmsExperimentEvent, CmsMedia, CmsPage, CmsPageVersion, CmsSite
    from app.services import cms_personalize as pz
    from app.services import cms_service as cms
    from app.services import web_analytics_service as wa
    async with AsyncSessionLocal() as db:
        s = CmsSite(key=f"b{uuid.uuid4().hex[:6]}", name="POVU bounds", locales=["en"], default_locale="en", theme={}, nav=[], require_approval=False)
        db.add(s)
        await db.flush()
        for k in ("one", "two"):
            db.add(CmsCta(site_id=s.id, key=k, label=k, href="/", views=0, clicks=0))
        pages = []
        for i in range(3):
            p = CmsPage(site_id=s.id, kind="PAGE", locale="en", translation_group=uuid.uuid4(), slug=f"p{i}", path=f"/p{i}", title=f"P{i}",
                        draft={"blocks": [], "seo": {}}, status="DRAFT", access="PUBLIC", tags=[])
            db.add(p)
            pages.append(p)
        await db.flush()
        user = type("U", (), {"username": "tester", "id": None, "email": None, "full_name": None})()
        for p in pages:
            await cms.publish(db, p, user, content={"blocks": [], "seo": {}})
        await db.flush()
        # sitemap bounded
        monkeypatch.setattr(cms, "SITEMAP_MAX", 2)
        assert (await cms.sitemap(db, s)).count("<loc>") == 2
        # expansion bounded: the second CTA beyond the budget is dropped
        monkeypatch.setattr(cms, "EXPAND_BUDGET", 1)
        out = await cms.expand(db, s, [{"type": "cta", "cta_key": "one"}, {"type": "cta", "cta_key": "two"}])
        assert [b["cta"]["key"] for b in out] == ["one"]
        # first experiment row is race-safe (second create attempt reuses the row)
        e1 = await pz._experiment(db, pages[0], "hero", ["a", "b"])
        e2 = await pz._experiment(db, pages[0], "hero", ["a", "b"])
        assert e1.id == e2.id
        assert (await db.execute(select(func.count()).select_from(CmsExperiment).where(CmsExperiment.page_id == pages[0].id))).scalar_one() == 1
        # retention: old attribution rows go with the analytics purge
        old = datetime.now(timezone.utc) - timedelta(days=settings.WEB_ANALYTICS_RETENTION_DAYS + 5)
        db.add(CmsExperimentEvent(experiment_id=e1.id, visitor_hash="x" * 64, variant="a", kind="VIEW", created_at=old))
        db.add(CmsExperimentEvent(experiment_id=e1.id, visitor_hash="y" * 64, variant="a", kind="VIEW"))
        await db.flush()
        await wa.purge_expired(db)
        left = (await db.execute(select(CmsExperimentEvent.visitor_hash).where(CmsExperimentEvent.experiment_id == e1.id))).scalars().all()
        assert left == ["y" * 64]
        # podcast feed: channel link + description
        show = f"POVU Talk {uuid.uuid4().hex[:4]}"
        db.add(CmsMedia(kind="AUDIO", title="Episode 1", mime="audio/wav", size=10, sha256="0" * 64, storage_path=uuid.uuid4().hex,
                        captions={}, podcast=show, public=True))
        await db.commit()
    async with _client() as c:
        feed = (await c.get(f"/api/v1/public/cms/podcast/{show}.xml")).text
    assert "<link>" in feed and "<description>" in feed and "Episode 1" in feed
    async with AsyncSessionLocal() as db:
        await db.execute(CmsPageVersion.__table__.delete().where(CmsPageVersion.page_id.in_([p.id for p in pages])))
        await db.commit()


@DB
@pytest.mark.asyncio
async def test_oversized_upload_refused_before_reading(monkeypatch):
    from sqlalchemy import select
    from app.core.config import settings
    from app.core.security import hash_password
    from app.db.session import AsyncSessionLocal
    from app.models.role import Permission, Role
    from app.models.user import User
    pw = uuid.uuid4().hex + "Aa1!"
    async with AsyncSessionLocal() as db:
        u = User(username=f"up-{uuid.uuid4().hex[:6]}", email=f"up-{uuid.uuid4().hex[:6]}@povu-demo.test", full_name="Up",
                 hashed_password=hash_password(pw), is_active=True)
        role = Role(name=f"up-{uuid.uuid4().hex[:6]}", is_active=True)
        for code in ("marketing.view", "marketing.create"):
            p = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one_or_none()
            if p is None:
                p = Permission(code=code, name=code, module="marketing", action=code.split(".")[1], is_active=True)
                db.add(p)
                await db.flush()
            role.permissions.append(p)
        u.roles.append(role)
        db.add_all([role, u])
        await db.commit()
        name = u.username
    monkeypatch.setattr(settings, "MEDIA_MAX_UPLOAD_BYTES", 1000)
    async with _client() as c:
        assert (await c.post("/api/v1/auth/login", data={"username": name, "password": pw})).status_code == 200
        r = await c.post("/api/v1/cms/media", data={"title": "big"}, files={"file": ("big.mp4", b"\x00" * 200_000, "video/mp4")})
    assert r.status_code == 413
