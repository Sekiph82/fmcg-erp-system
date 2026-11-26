"""M47.S01.T011 report-builder datasets + M47.S01.T003 catalog fix (DB part needs M46_DB=1).

Every catalog source runs against the real schema (8 of 14 used to name columns that do not exist); an uploaded CSV
dataset is typed, blended with the customers source by code, filtered, and only writers may create datasets.
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


def test_csv_parsing_types_and_limits():
    from app.services import report_dataset_service as rds
    cols, rows = rds.parse_csv("Customer Code,Sell-out units,Week\nC-1,1,200,W47\nC-2,90,W47\n")
    assert [c["path"] for c in cols] == ["customer_code", "sell_out_units", "week"]
    assert cols[1]["type"] == "number" and rows[1]["sell_out_units"] == 90.0
    with pytest.raises(rds.DatasetError):
        rds.parse_csv("")


@DB
@pytest.mark.asyncio
async def test_all_catalog_sources_run():
    from app.db.session import AsyncSessionLocal
    from app.services import report_builder_service as rbs
    async with AsyncSessionLocal() as db:
        for key, src in rbs.DATA_SOURCES.items():
            out = await rbs._execute_query(db, key, [{"path": f["path"]} for f in src["fields"]], [], 5, 0)
            assert "error" not in out, (key, out.get("error"))
            await db.rollback()


@DB
@pytest.mark.asyncio
async def test_dataset_blend_and_permissions():
    from sqlalchemy import select
    from app.core.security import hash_password
    from app.db.session import AsyncSessionLocal
    from app.models.role import Permission, Role
    from app.models.sales import Customer
    from app.models.user import User
    code = f"DS-{uuid.uuid4().hex[:5]}"
    async with AsyncSessionLocal() as db:
        db.add(Customer(code=code, name="POVU Duka Moja", currency="KES", region="Nairobi"))
        names = {}
        for tag, perms in (("analyst", ("reports.view", "reports.create", "reports.run")), ("viewer", ("reports.view",))):
            u = User(username=f"{tag}-{uuid.uuid4().hex[:6]}", email=f"{tag}-{uuid.uuid4().hex[:6]}@povu-demo.test", full_name=tag,
                     hashed_password=hash_password(PW), is_active=True)
            role = Role(name=f"{tag}-{uuid.uuid4().hex[:6]}", is_active=True)
            for c in perms:
                p = (await db.execute(select(Permission).where(Permission.code == c))).scalar_one_or_none()
                if p is None:
                    p = Permission(code=c, name=c, module="reports", action=c.split(".")[1], is_active=True)
                    db.add(p)
                    await db.flush()
                role.permissions.append(p)
            u.roles.append(role)
            db.add_all([role, u])
            names[tag] = u.username
        await db.commit()
    from app.main import app
    csv = f"customer_code,units,week\n{code},120,W47\nUNKNOWN-9,5,W47\n"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as a, \
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://erp.test") as v:
        for c, n in ((a, "analyst"), (v, "viewer")):
            assert (await c.post("/api/v1/auth/login", data={"username": names[n], "password": PW})).status_code == 200
        assert (await v.post("/api/v1/report-datasets", json={"name": "x", "csv": csv})).status_code == 403
        bad = await a.post("/api/v1/report-datasets", json={"name": "Sell-out", "csv": csv, "join_source": "customers",
                                                             "join_local": "nope", "join_remote": "customer_code"})
        assert bad.status_code == 422
        d = (await a.post("/api/v1/report-datasets", json={"name": "Sell-out W47", "csv": csv, "join_source": "customers",
                                                           "join_local": "customer_code", "join_remote": "customer_code"})).json()
        assert d["row_count"] == 2 and d["source_key"].startswith("ds:")
        cat = (await a.get("/api/v1/reports-builder/catalog")).json()
        assert d["source_key"] in cat and any(f["path"] == "src.region" for f in cat[d["source_key"]]["fields"])
        prev = (await v.get(f"/api/v1/report-datasets/{d['id']}/preview")).json()
        rows = {r["customer_code"]: r for r in prev["rows"]}
        assert rows[code]["src.region"] == "Nairobi" and rows[code]["src.customer_name"] == "POVU Duka Moja"
        assert rows["UNKNOWN-9"]["src.region"] is None                       # left join: unmatched rows kept
    async with AsyncSessionLocal() as db:
        from types import SimpleNamespace
        from app.services import report_builder_service as rbs
        user = SimpleNamespace(id=None, username="x", is_superuser=True, roles=[], access_scopes=[])
        out = await rbs._execute_query(db, d["source_key"], [{"path": "customer_code"}, {"path": "units"}],
                                       [{"field_path": "units", "operator": "gt", "value": "10"}], 10, 0, user=user)
        assert out["rows"] == [{"customer_code": code, "units": "120.0"}]
        assert "error" in await rbs._execute_query(db, d["source_key"], [], [], 10, 0, user=None)
