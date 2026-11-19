"""M38.S06 scan-driven warehouse execution on disposable PostgreSQL through the real app: the picker scans the pick
location and item (wrong location/item refused, short picks need a reason, other people's tasks refused); the putaway
operator scans item and target location (location must be in the task's warehouse; off-suggestion needs a reason)."""
from __future__ import annotations

import os
import re
import uuid
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.deps import get_current_user
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Product, ProductCategory, Warehouse, WarehouseType
from app.models.inventory import Stock, StockType
from app.models.user import User
from app.models.wms import (PickingTask, PickingTaskStatus, PutawayTask, PutawayTaskStatus, StorageLocation, WarehouseZone,
                            ZoneType)

TASK_DB_ENV = "M38_S06_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M38_S06_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m38_s06_[a-f0-9]{24}")
pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")
W = "/api/v1/wms"


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _as(u, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".")[1], is_active=True) for c in codes]
    return SimpleNamespace(id=u.id, username=u.username, email=u.email, full_name=u.full_name, is_superuser=False, is_active=True,
                           access_scopes=[], roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_scan_pick_and_putaway():
    from app.main import app

    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        pk, other = User(email=f"pk-{s}@example.com", username=f"pk{s}", full_name="Picker", hashed_password="x"), \
            User(email=f"ot-{s}@example.com", username=f"ot{s}", full_name="Other", hashed_password="x")
        db.add_all([pk, other])
        whs = [Warehouse(code=f"W{n}-{s}", name=f"WH{n}", warehouse_type=list(WarehouseType)[0]) for n in (1, 2)]
        prod = Product(sku=f"SKU-{s}", barcode=f"BC{s}", name="Juice", category=ProductCategory.BEVERAGE)
        db.add_all([*whs, prod])
        await db.flush()
        locs = {}
        for n, wh in enumerate(whs):
            z = WarehouseZone(warehouse_id=wh.id, code=f"Z{n}-{s}", name="Zone", zone_type=list(ZoneType)[0])
            db.add(z)
            await db.flush()
            for code in ("A-01", "A-02"):
                loc = StorageLocation(zone_id=z.id, code=f"{code}", name=code, barcode=f"L{n}{code}-{s}")
                db.add(loc)
                await db.flush()
                locs[(n, code)] = loc
        pick = PickingTask(task_no=f"PK-{s}", warehouse_id=whs[0].id, product_id=prod.id, from_location_id=locs[(0, "A-01")].id,
                           requested_qty=Decimal("10"))
        mine = PickingTask(task_no=f"PK2-{s}", warehouse_id=whs[0].id, product_id=prod.id, requested_qty=Decimal("5"),
                           assigned_to_id=other.id)
        put = PutawayTask(task_no=f"PA-{s}", warehouse_id=whs[0].id, product_id=prod.id, quantity=Decimal("10"),
                          suggested_location_id=locs[(0, "A-02")].id)
        db.add_all([pick, mine, put])
        await db.flush()
        prod2 = Product(sku=f"SKU2-{s}", name="Water", category=ProductCategory.BEVERAGE)
        db.add(prod2)
        await db.flush()
        nostock = PutawayTask(task_no=f"PA0-{s}", warehouse_id=whs[0].id, product_id=prod2.id, quantity=Decimal("1"))
        db.add_all([nostock, Stock(stock_type=StockType.PRODUCT, warehouse_id=whs[0].id, product_id=prod.id, quantity_on_hand=Decimal("10"))])
        await db.commit()
        ids = SimpleNamespace(nostock=nostock.id, pick=pick.id, other_pick=mine.id, put=put.id, loc_w2=locs[(1, "A-01")].barcode,
                              l01=locs[(0, "A-01")].barcode, l02=locs[(0, "A-02")].barcode)
        P = _as(pk, "inventory.dispatch_all", "inventory.receive_all")  # the seeded warehouse_picker role: no inventory.view

    app.dependency_overrides[get_current_user] = lambda: P
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            listed = await c.get(f"{W}/picking/tasks?status=PENDING")                                   # the floor list works without inventory.view
            assert listed.status_code == 200 and {str(ids.pick), str(ids.other_pick)} <= {t["id"] for t in listed.json()}, listed.text
            url = f"{W}/picking/tasks/{ids.pick}/scan-confirm"
            ok = {"location_code": ids.l01, "item_code": f"bc{s}", "picked_qty": "10"}
            assert (await c.post(url, json={**ok, "location_code": ids.l02})).status_code == 422          # wrong bin
            assert (await c.post(url, json={**ok, "location_code": ids.loc_w2})).status_code == 422        # other warehouse
            assert (await c.post(url, json={**ok, "item_code": "OTHER"})).status_code == 422               # wrong item
            assert (await c.post(url, json={**ok, "picked_qty": "11"})).status_code == 422                 # over-pick
            assert (await c.post(url, json={**ok, "picked_qty": "8"})).status_code == 422                  # short, no reason
            r = await c.post(url, json={**ok, "picked_qty": "8", "short_reason": "only 8 in bin"})
            assert r.status_code == 200 and r.json()["status"] == "PICKED", r.text
            assert (await c.post(url, json=ok)).status_code == 409                                         # already picked
            assert (await c.post(f"{W}/picking/tasks/{ids.other_pick}/scan-confirm",
                                 json={**ok, "picked_qty": "5"})).status_code == 403                       # someone else's

            purl = f"{W}/putaway/tasks/{ids.put}/scan-execute"
            assert (await c.post(purl, json={"location_code": ids.loc_w2, "item_code": f"SKU-{s}"})).status_code == 422
            assert (await c.post(purl, json={"location_code": ids.l01, "item_code": f"SKU-{s}"})).status_code == 422  # off-suggestion, no reason
            assert (await c.post(f"{W}/putaway/tasks/{ids.nostock}/scan-execute",
                                 json={"location_code": "a-01", "item_code": f"SKU2-{s}"})).status_code == 409  # nothing to move
            assert (await c.post(url.replace(str(ids.pick), str(ids.other_pick)), json={**ok, "item_code": "LOT-ONLY"})).status_code in (403, 422)
            done = await c.post(purl, json={"location_code": "a-02", "item_code": f"SKU-{s}"})                       # by code, case-insensitive
            assert done.status_code == 200 and done.json()["actual_location_code"] == "A-02", done.text
        app.dependency_overrides[get_current_user] = lambda: _as(other, "inventory.view")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
            assert (await c.post(f"{W}/picking/tasks/{ids.other_pick}/scan-confirm",
                                 json={"location_code": ids.l01, "item_code": f"BC{s}", "picked_qty": "5"})).status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    async with AsyncSessionLocal() as db:
        t = await db.get(PickingTask, ids.pick)
        assert (t.status, t.picked_qty) == (PickingTaskStatus.PICKED, Decimal("8.000")) and "only 8 in bin" in t.notes
        assert (await db.get(PutawayTask, ids.put)).status == PutawayTaskStatus.COMPLETED
        moved = (await db.execute(select(Stock).where(Stock.product_id == t.product_id))).scalars().all()
        assert [m.location_id is not None for m in moved] == [True]
