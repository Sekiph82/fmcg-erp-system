"""M40.S02.T001 record lookup for pickers on disposable PostgreSQL: every kind resolves, search works, results carry
only id + label, and each kind needs its module's view right."""
from __future__ import annotations

import os
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1.endpoints import lookup
from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot

TASK_DB_ENV = "M40_S02_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M40_S02_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m40_s02_t001_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _user(*codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uuid4(), is_superuser=False, access_scopes=[], company_id=None,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_lookup_kinds_search_and_rights():
    s = uuid4().hex[:8]
    admin = SimpleNamespace(id=uuid4(), is_superuser=True)
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]

        for kind in lookup.KINDS:   # every registered kind queries without error
            rows = await lookup.search(kind, None, 5, db, admin)
            assert all(set(r) == {"id", "label", "sub"} for r in rows), kind

        lot = Lot(lot_number=f"POVU-LOT-{s}", batch_number=f"B-{s}")
        db.add(lot)
        await db.commit()
        found = await lookup.search("lot", f"lot-{s}", 20, db, _user("inventory.view"))
        assert [r["label"] for r in found] == [f"POVU-LOT-{s}"] and found[0]["id"] == str(lot.id)
        assert (await lookup.one("lot", lot.id, db, _user("quality.view")))["label"] == f"POVU-LOT-{s}"
        assert await lookup.search("lot", "%", 20, db, admin) is not None        # LIKE wildcards are neutralised

        with pytest.raises(HTTPException) as e:                                # no module right → 403
            await lookup.search("lot", None, 5, db, _user("hr.view"))
        assert e.value.status_code == 403
        with pytest.raises(HTTPException) as e:
            await lookup.search("candidate", None, 5, db, _user("sales.view"))
        assert e.value.status_code == 403
        with pytest.raises(HTTPException) as e:
            await lookup.search("not_a_kind", None, 5, db, admin)
        assert e.value.status_code == 404
