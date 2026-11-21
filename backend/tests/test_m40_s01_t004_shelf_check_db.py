"""M40.S01.T004 merchandiser shelf check on disposable PostgreSQL: a rep records facings / out-of-stock / price /
planogram per product on their own visit (re-sending corrects it), photos, and the supervisor report."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select

from app.api.v1.endpoints import field_app as f
from app.db.session import AsyncSessionLocal, engine
from app.models.field_sales import SalesRep, ShelfCheck, VisitLog
from app.models.master import Product, ProductCategory
from app.models.sales import Customer, CustomerChannel
from app.models.user import User

TASK_DB_ENV = "M40_S01_T004_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M40_S01_T004_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m40_s01_t004_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


def _as(uid, *codes):
    perms = [SimpleNamespace(code=c, module=c.split(".")[0], action=c.split(".", 1)[1], is_active=True) for c in codes]
    return SimpleNamespace(id=uid, is_superuser=False, access_scopes=[], company_id=None,
                           roles=[SimpleNamespace(name="r", is_active=True, permissions=perms, access_scopes=[])])


@pytest.mark.asyncio
async def test_shelf_check_flow_and_report():
    s = uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        u1 = User(email=f"m1-{s}@povu.example", username=f"m1{s}", full_name="Mary Merch", hashed_password="x")
        u2 = User(email=f"m2-{s}@povu.example", username=f"m2{s}", full_name="Other Rep", hashed_password="x")
        db.add_all([u1, u2])
        await db.flush()
        r1 = SalesRep(code=f"R1-{s}", name="Mary Merch", user_id=u1.id)
        r2 = SalesRep(code=f"R2-{s}", name="Other Rep", user_id=u2.id)
        shop = Customer(code=f"SH-{s}", name=f"Mama Duka {s}", channel=CustomerChannel.DISTRIBUTOR, currency="KES")
        ld = Product(sku=f"POVU-LD-{s}", name=f"POVU Liquid Detergent 1L {s}", category=ProductCategory.HOUSEHOLD)
        ac = Product(sku=f"POVU-AC-{s}", name=f"POVU AllClean 500ml {s}", category=ProductCategory.HOUSEHOLD)
        db.add_all([r1, r2, shop, ld, ac])
        await db.flush()
        v = VisitLog(rep_id=r1.id, customer_id=shop.id, visit_date=date.today())
        db.add(v)
        await db.commit()
        me, other, boss = _as(u1.id), _as(u2.id), _as(u2.id, "field.supervise")
        vid, ld_id, ac_id = v.id, ld.id, ac.id

        with pytest.raises(ValidationError):
            f.ShelfLineIn(product_id=ld_id, facings=-1)
        lines = [f.ShelfLineIn(product_id=ld_id, facings=6, shelf_price=Decimal("250"), planogram_ok=True),
                 f.ShelfLineIn(product_id=ac_id, facings=3, out_of_stock=True, planogram_ok=False)]
        rows = await f.save_shelf(vid, f.ShelfIn(lines=lines), db, me)
        got = {r["product_id"]: r for r in rows}
        assert got[str(ld_id)]["facings"] == 6 and got[str(ld_id)]["shelf_price"] == 250.0
        assert got[str(ac_id)]["out_of_stock"] and got[str(ac_id)]["facings"] == 0        # out of stock → no facings

        # correcting a product replaces its line (one line per visit and product)
        await f.save_shelf(vid, f.ShelfIn(lines=[f.ShelfLineIn(product_id=ld_id, facings=8, shelf_price=Decimal("240"))]), db, me)
        assert (await db.execute(select(func.count()).select_from(ShelfCheck).where(ShelfCheck.visit_id == vid))).scalar_one() == 2
        assert {r["product_id"]: r["facings"] for r in await f.shelf_of_visit(vid, db, me)}[str(ld_id)] == 8

        # someone else's visit, duplicate products, unknown products
        with pytest.raises(HTTPException) as e:
            await f.save_shelf(vid, f.ShelfIn(lines=lines), db, other)
        assert e.value.status_code == 404
        with pytest.raises(HTTPException) as e:
            await f.save_shelf(vid, f.ShelfIn(lines=[lines[0], lines[0]]), db, me)
        assert e.value.status_code == 422
        with pytest.raises(HTTPException) as e:
            await f.save_shelf(vid, f.ShelfIn(lines=[f.ShelfLineIn(product_id=uuid4(), facings=1)]), db, me)
        assert e.value.status_code == 422

        # supervisor report: only with field.supervise
        with pytest.raises(HTTPException):
            await f.shelf_report(7, db, other)
        rep = await f.shelf_report(7, db, boss)
        by = {p["sku"]: p for p in rep["products"]}
        assert by[f"POVU-AC-{s}"]["outlets_out_of_stock"] == 1 and by[f"POVU-AC-{s}"]["planogram_compliance_pct"] == 0
        assert by[f"POVU-LD-{s}"]["avg_facings"] == 8.0 and by[f"POVU-LD-{s}"]["min_price"] == 240.0
        assert any(o["product"].startswith("POVU AllClean") and o["rep"] == "Mary Merch" for o in rep["out_of_stock"])
