"""M47.S01.T011 point-and-click event tags (DB part needs M46_DB=1): tags map plain CSS selectors to ACTIVE event
definitions; the public endpoint serves only active tags and no visitor data; markup/at-rules are refused."""
import os
import uuid

import pytest

DB = pytest.mark.skipif(os.environ.get("M46_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine():
    yield
    if os.environ.get("M46_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


def test_selector_guard():
    from app.services.web_analytics_service import TAG_SELECTOR_BAD as bad
    assert not bad.search("#order-now > a.btn:nth-of-type(2)") and not bad.search(r"#a\:b")
    for s in ("a{color:red}", "<script>", "@import x", "div;x", "a[style*=url(x)]"):
        assert bad.search(s)


@DB
@pytest.mark.asyncio
async def test_tags_need_active_definitions_and_public_view_filters():
    import httpx
    from app.db.session import AsyncSessionLocal
    from app.main import app
    from app.models.m47_automation import WebEventDefinition
    from app.services import web_analytics_service as wa
    ev, old = f"order_click_{uuid.uuid4().hex[:4]}", f"old_{uuid.uuid4().hex[:4]}"
    async with AsyncSessionLocal() as db:
        db.add_all([WebEventDefinition(name=ev, properties={}, active=True), WebEventDefinition(name=old, properties={}, active=True)])
        await db.commit()
        with pytest.raises(ValueError):
            await wa.save_event_tags(db, [{"selector": "#buy", "event": "undefined_event"}], "t")
        with pytest.raises(ValueError):
            await wa.save_event_tags(db, [{"selector": "a{x}", "event": ev}], "t")
        saved = await wa.save_event_tags(db, [{"selector": "#order-now", "event": ev}, {"selector": ".legacy", "event": old}], "t")
        await db.commit()
        assert len(saved) == 2
        d = (await db.execute(__import__("sqlalchemy").select(WebEventDefinition).where(WebEventDefinition.name == old))).scalar_one()
        d.active = False                                    # deactivated events stop being tagged on the website
        await db.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as c:
        pub = (await c.get("/api/v1/public/web/tags")).json()
    assert pub == [{"selector": "#order-now", "event": ev}]
