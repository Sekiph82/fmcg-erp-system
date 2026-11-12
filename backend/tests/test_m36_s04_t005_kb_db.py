"""M36.S04.T005 knowledge base on disposable PostgreSQL through the real app: editorial publish gate,
public help centre shows only published public articles, feedback with public rate limit."""
from __future__ import annotations

import os
import re
import uuid
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.deps import get_current_user
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User

TASK_DB_ENV = "M36_S04_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M36_S04_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m36_s04_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(uid, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, is_superuser=False, is_active=True, access_scopes=[], username=str(uid)[:8],
                           full_name="u", email="u@example.invalid",
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_publish_gate_public_help_centre_and_feedback():
    from app.main import app

    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        ed = User(email=f"ed-{s}@example.invalid", username=f"ed{s}", full_name="Editor", hashed_password="x")
        pub = User(email=f"pub-{s}@example.invalid", username=f"pub{s}", full_name="Publisher", hashed_password="x")
        db.add_all([ed, pub])
        await db.commit()
        editor = _user(ed.id, "knowledge_base.view", "knowledge_base.create", "knowledge_base.edit")
        publisher = _user(pub.id, "knowledge_base.view", "knowledge_base.edit", "knowledge_base.publish")

    transport = httpx.ASGITransport(app=app, client=("192.0.2.44", 1))
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            app.dependency_overrides[get_current_user] = lambda: editor
            body = {"slug": f"cap-{s}", "title": f"Closing caps {s}", "content_md": "Turn until it clicks.", "is_internal_only": False}
            assert (await c.post("/api/v1/kb/articles", json={**body, "status": "PUBLISHED"})).status_code == 403
            assert (await c.post("/api/v1/kb/articles", json=body)).status_code == 403          # making it public
            art = (await c.post("/api/v1/kb/articles", json={**body, "is_internal_only": True})).json()
            secret = (await c.post("/api/v1/kb/articles", json={"slug": f"secret-{s}", "title": f"Secret {s}",
                                                                "content_md": "internal margins"})).json()
            assert (await c.patch(f"/api/v1/kb/articles/{art['id']}", json={"status": "LIVE"})).status_code == 422
            assert (await c.patch(f"/api/v1/kb/articles/{art['id']}", json={"status": "IN_REVIEW"})).status_code == 200
            assert (await c.patch(f"/api/v1/kb/articles/{art['id']}", json={"status": "PUBLISHED"})).status_code == 403

            app.dependency_overrides[get_current_user] = lambda: publisher
            ok = await c.patch(f"/api/v1/kb/articles/{art['id']}", json={"status": "PUBLISHED", "is_internal_only": False})
            assert ok.status_code == 200
            assert (await c.patch(f"/api/v1/kb/articles/{secret['id']}", json={"status": "PUBLISHED"})).status_code == 200

            app.dependency_overrides[get_current_user] = lambda: editor
            assert (await c.patch(f"/api/v1/kb/articles/{art['id']}", json={"content_md": "changed"})).status_code == 403
            assert (await c.patch(f"/api/v1/kb/articles/{art['id']}", json={"company_id": str(uuid.uuid4())})).status_code == 403
            assert (await c.patch(f"/api/v1/kb/articles/{secret['id']}", json={"is_internal_only": 0})).status_code == 422
            fb = await c.post(f"/api/v1/kb/articles/{art['id']}/feedback", json={"helpful": True})
            assert fb.json() == {"helpful": 1, "not_helpful": 0}
            detail = await c.get(f"/api/v1/kb/articles/{art['id']}")
            assert detail.status_code == 200 and detail.json()["feedback"] == {"helpful": 1, "not_helpful": 0}
            app.dependency_overrides.pop(get_current_user, None)

            # public help centre: no login, only the published public article
            found = (await c.get(f"/api/v1/public/kb/search?q={s}")).json()
            assert [a["slug"] for a in found] == [f"cap-{s}"]                       # published-but-internal stays private
            assert (await c.get(f"/api/v1/public/kb/articles/secret-{s}")).status_code == 404
            pa = await c.get(f"/api/v1/public/kb/articles/cap-{s}")
            assert pa.status_code == 200 and pa.json()["content_md"] == "Turn until it clicks.", pa.text
            assert (await c.get("/api/v1/kb/articles")).status_code == 401           # internal API still needs login
            codes = [(await c.post(f"/api/v1/public/kb/articles/cap-{s}/feedback", json={"helpful": False})).status_code
                     for _ in range(11)]
            assert codes[:10] == [202] * 10 and codes[10] == 429
    finally:
        app.dependency_overrides.pop(get_current_user, None)
