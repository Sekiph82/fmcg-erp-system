"""M48.S01.T018 / T019 on disposable PostgreSQL through the real app (needs M48_DB=1).

T018: a stock transfer sent again with the same idempotency_key (retry, double click, two requests racing) returns the
first movement and moves stock once; the key cannot be reused for another transfer or by another user; no key still works.
T019: a count adjustment's stock movement carries the counted warehouse, and a count that cannot tell which of several
stock rows (lots/locations) it counted is refused with a clear 400 — at entry and at approval — instead of crashing.
"""
import asyncio
import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from tests.test_m48_s01_t014_scan_flows import _barcode, _client, _guard_db, _person, _qty, _scan

pytestmark = pytest.mark.skipif(os.environ.get("M48_DB") != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest.fixture(autouse=True)
async def _dispose_engine(monkeypatch):
    from app.core import token_blocklist
    monkeypatch.setattr(token_blocklist, "_get_redis", lambda: None)     # in-memory blocklist: never the dev Redis
    yield
    if os.environ.get("M48_DB") == "1":
        from app.db.session import engine
        await engine.dispose()


async def _stock_row(db, wh, product, qty, lot=None):
    from app.models.inventory import Stock, StockType
    db.add(Stock(stock_type=StockType.PRODUCT, warehouse_id=wh, product_id=product, lot_id=lot, quantity_on_hand=Decimal(qty),
                 quantity_reserved=Decimal("0"), quantity_available=Decimal(qty)))


async def test_transfer_idempotency_key():
    from app.db.session import AsyncSessionLocal
    from app.models.inventory import StockMovement
    from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType

    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        clerk, _ = await _person(db, "inventory.view", "inventory.transfer_all")
        other, _ = await _person(db, "inventory.view", "inventory.transfer_all")
        a = Warehouse(code=f"M48-T18-A-{s}", name=f"POVU FG Nairobi {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        b = Warehouse(code=f"M48-T18-B-{s}", name=f"POVU FG Nakuru {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        p = Product(sku=f"POVU-ALC-1L-{s}", barcode=_barcode(s), name=f"POVU AllClean 1 L {s}",
                    category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
        db.add_all([a, b, p])
        await db.flush()
        await _stock_row(db, a.id, p.id, "100")
        await db.commit()
        ids = dict(a=a.id, b=b.id, p=p.id)

    def move(qty="10", key=None):
        body = {"product_id": str(ids["p"]), "from_warehouse_id": str(ids["a"]), "to_warehouse_id": str(ids["b"]),
                "quantity": qty, "reference": f"M48-TRF-{s}"}
        return {**body, "idempotency_key": key} if key else body

    url = "/api/v1/inventory/stock/transfer"
    k1, k2 = f"povu-{uuid.uuid4()}", f"povu-{uuid.uuid4()}"
    async with _client(clerk) as c:
        first = await c.post(url, json=move(key=k1))
        assert first.status_code == 201, first.text
        again = await c.post(url, json=move(key=k1))                                 # retry / double click
        assert again.status_code == 201 and again.json()["id"] == first.json()["id"], again.text
        assert (await c.post(url, json=move("11", key=k1))).status_code == 409        # same key, other transfer
        assert (await c.post(url, json=move(key="short"))).status_code == 422         # key too short
        racing = await asyncio.gather(*[c.post(url, json=move("5", key=k2)) for _ in range(3)])   # concurrent replays
        assert {r.status_code for r in racing} == {201}, [r.text for r in racing]
        assert len({r.json()["id"] for r in racing}) == 1
        assert (await c.post(url, json=move("1"))).status_code == 201                 # no key: still accepted
    async with _client(other) as c:
        assert (await c.post(url, json=move(key=k1))).status_code == 409              # someone else's key

    async with AsyncSessionLocal() as db:
        assert await _qty(db, warehouse_id=ids["a"], product_id=ids["p"]) == Decimal("84")   # 100 - 10 - 5 - 1
        assert await _qty(db, warehouse_id=ids["b"], product_id=ids["p"]) == Decimal("16")
        n = (await db.execute(select(func.count()).select_from(StockMovement)
                              .where(StockMovement.idempotency_key.in_([k1, k2])))).scalar_one()
        assert n == 2


async def test_count_adjustment_warehouse_and_ambiguity():
    from app.db.session import AsyncSessionLocal
    from app.models.cycle_count import CountEntry, CycleCountPlan, CycleCountTask, PlanType
    from app.models.inventory import Lot, StockMovement
    from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType

    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        counter, _ = await _person(db, "inventory.view", "cycle_count.view", "cycle_count.create", "cycle_count.approve")
        wh = Warehouse(code=f"M48-T19-{s}", name=f"POVU FG Eldoret {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        single = Product(sku=f"POVU-HWP-1KG-{s}", barcode=_barcode(s), name=f"POVU Hand Wash Powder 1 kg Pouch {s}",
                         category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
        lots = Product(sku=f"POVU-ALC-1L-{s}", barcode=_barcode(s[::-1]), name=f"POVU AllClean 1 L {s}",
                       category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
        later = Product(sku=f"POVU-ALC-5L-{s}", barcode=_barcode(s[4:] + s[:4]), name=f"POVU AllClean 5 L {s}",
                        category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
        pend = Product(sku=f"POVU-WC-1KG-{s}", barcode=_barcode(s[2:] + s[:2]), name=f"POVU WhiteCare 1 kg {s}",
                       category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
        db.add_all([wh, single, lots, later, pend])
        await db.flush()
        l1, l2 = Lot(lot_number=f"ALC-L1-{s}", product_id=lots.id), Lot(lot_number=f"ALC-L2-{s}", product_id=lots.id)
        db.add_all([l1, l2])
        await db.flush()
        await _stock_row(db, wh.id, single.id, "100")
        await _stock_row(db, wh.id, lots.id, "30", l1.id)
        await _stock_row(db, wh.id, lots.id, "20", l2.id)
        await _stock_row(db, wh.id, later.id, "50")
        await _stock_row(db, wh.id, pend.id, "50")
        plan = CycleCountPlan(plan_code=f"M48-T19-{s}", name="POVU FG weekly", warehouse_id=wh.id, plan_type=PlanType.ITEM,
                              variance_tolerance_pct=Decimal("2.0"), auto_approve_within_tolerance=True)
        db.add(plan)
        await db.flush()
        tasks = {k: CycleCountTask(task_no=f"M48-T19-{k}-{s}", plan_id=plan.id, warehouse_id=wh.id, product_id=pid,
                                   scheduled_date=date.today()) for k, pid in (("one", single.id), ("lots", lots.id),
                                                                              ("later", later.id), ("pend", pend.id))}
        db.add_all(tasks.values())
        await db.commit()
        ids = dict(pend=pend.id, wh=wh.id, single=single.id, lots=lots.id, later=later.id, l1=l1.id, l2=l2.id,
                   **{f"t_{k}": t.id for k, t in tasks.items()})

    url = "/api/v1/cycle-count/entries"
    async with _client(counter) as c:
        (tid,) = await _scan(c, "count_task", f"M48-T19-one-{s}")
        r = await c.post(url, json={"task_id": tid, "counted_qty": "99", "unit": "PCS"})      # 1% short → auto-posted
        assert r.status_code == 201, r.text

        amb = await c.post(url, json={"task_id": str(ids["t_lots"]), "counted_qty": "50", "unit": "PCS"})
        assert amb.status_code == 400 and "lot or location" in amb.text, amb.text
        r = await c.post(url, json={"task_id": str(ids["t_lots"]), "lot_id": str(ids["l2"]), "counted_qty": "19.8",
                                    "unit": "PCS"})                                         # the counted lot, 1% short
        assert r.status_code == 201, r.text

        r = await c.post(url, json={"task_id": str(ids["t_pend"]), "counted_qty": "56", "unit": "PCS"})    # 12% over → pending
        assert r.status_code == 201 and r.json()["within_tolerance"] is False, r.text
        ok = await c.post("/api/v1/cycle-count/adjustments/approve", json={"entry_ids": [r.json()["id"]]})
        assert ok.status_code == 200 and ok.json()["approved"] == 1, ok.text              # was a 500 (lazy load)

        r = await c.post(url, json={"task_id": str(ids["t_later"]), "counted_qty": "40", "unit": "PCS"})  # 20% → pending
        assert r.status_code == 201 and r.json()["within_tolerance"] is False, r.text
        pending = r.json()["id"]
        async with AsyncSessionLocal() as db:                                  # a second lot arrives before approval
            lot = Lot(lot_number=f"ALC5-L9-{s}", product_id=ids["later"])
            db.add(lot)
            await db.flush()
            await _stock_row(db, ids["wh"], ids["later"], "10", lot.id)
            await db.commit()
        r = await c.post("/api/v1/cycle-count/adjustments/approve", json={"entry_ids": [pending]})
        assert r.status_code == 400 and "lot or location" in r.text, r.text

    async with AsyncSessionLocal() as db:
        assert await _qty(db, warehouse_id=ids["wh"], product_id=ids["single"]) == Decimal("99")
        assert await _qty(db, warehouse_id=ids["wh"], product_id=ids["lots"], lot_id=ids["l1"]) == Decimal("30")
        assert await _qty(db, warehouse_id=ids["wh"], product_id=ids["lots"], lot_id=ids["l2"]) == Decimal("19.8")
        assert await _qty(db, warehouse_id=ids["wh"], product_id=ids["later"]) == Decimal("60")       # untouched
        assert await _qty(db, warehouse_id=ids["wh"], product_id=ids["pend"]) == Decimal("56")        # approved surplus
        (gain,) = (await db.execute(select(StockMovement).where(StockMovement.product_id == ids["pend"]))).scalars().all()
        assert (gain.destination_warehouse_id, gain.source_warehouse_id) == (ids["wh"], None)
        assert (await db.execute(select(func.count()).select_from(CountEntry)
                                 .where(CountEntry.task_id == ids["t_lots"]))).scalar_one() == 1       # refusal stored nothing
        moves = (await db.execute(select(StockMovement).where(StockMovement.product_id.in_([ids["single"], ids["lots"]]),
                                                               StockMovement.notes.like("Cycle count adjustment%")))).scalars().all()
        assert len(moves) == 2 and all(m.source_warehouse_id == ids["wh"] and m.destination_warehouse_id is None
                                       for m in moves)                       # shortages leave the counted warehouse


# ── M48 review follow-ups (#6 stranded/raced count adjustments, #8 lot on transfer replay) ─────────────────────────

async def _count_setup(db, s, qty="100"):
    from app.models.cycle_count import CycleCountPlan, CycleCountTask, PlanType
    from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType
    wh = Warehouse(code=f"M48-R6-{s}", name=f"POVU FG Thika {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
    p = Product(sku=f"POVU-HWP-1KG-{s}", barcode=_barcode(s), name=f"POVU Hand Wash Powder 1 kg Pouch {s}",
                category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
    db.add_all([wh, p])
    await db.flush()
    await _stock_row(db, wh.id, p.id, qty)
    plan = CycleCountPlan(plan_code=f"M48-R6-{s}", name="POVU FG weekly", warehouse_id=wh.id, plan_type=PlanType.ITEM,
                          variance_tolerance_pct=Decimal("2.0"), auto_approve_within_tolerance=True)
    db.add(plan)
    await db.flush()
    task = CycleCountTask(task_no=f"M48-R6-{s}", plan_id=plan.id, warehouse_id=wh.id, product_id=p.id, scheduled_date=date.today())
    db.add(task)
    return wh, p, task


async def test_count_posting_failure_does_not_strand(monkeypatch):
    from fastapi import HTTPException
    from app.db.session import AsyncSessionLocal
    from app.models.cycle_count import CountAdjustment, CountEntry
    from app.services import cycle_count_service as ccs

    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        counter, _ = await _person(db, "inventory.view", "cycle_count.view", "cycle_count.create")
        wh, p, task = await _count_setup(db, s)
        await db.commit()
        ids = dict(wh=wh.id, p=p.id, task=task.id)

    async def gl_down(*a, **k):
        raise HTTPException(422, "No active accounting rule inventory/STOCK_ADJUSTMENT (test).")

    body = {"task_id": str(ids["task"]), "counted_qty": "99", "unit": "PCS"}
    async with _client(counter) as c:
        monkeypatch.setattr(ccs, "_post_adjustment_to_gl", gl_down)
        r = await c.post("/api/v1/cycle-count/entries", json=body)
        assert r.status_code == 422, r.text
        monkeypatch.undo()
        from app.core import token_blocklist                                 # undo() also restored this one
        monkeypatch.setattr(token_blocklist, "_get_redis", lambda: None)
        async with AsyncSessionLocal() as db:                                   # nothing stranded
            n = (await db.execute(select(func.count()).select_from(CountEntry).where(CountEntry.task_id == ids["task"]))).scalar_one()
            assert n == 0
            assert await _qty(db, warehouse_id=ids["wh"], product_id=ids["p"]) == Decimal("100")
        r = await c.post("/api/v1/cycle-count/entries", json=body)              # the recount is not blocked
        assert r.status_code == 201, r.text
    async with AsyncSessionLocal() as db:
        assert await _qty(db, warehouse_id=ids["wh"], product_id=ids["p"]) == Decimal("99")
        adj = (await db.execute(select(CountAdjustment).join(CountEntry, CountEntry.id == CountAdjustment.entry_id)
                                .where(CountEntry.task_id == ids["task"]))).scalar_one()
        assert adj.posted_flag is True


async def test_concurrent_duplicate_count_posts_once():
    from app.db.session import AsyncSessionLocal
    from app.models.cycle_count import CountEntry
    from app.models.inventory import StockMovement

    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        counter, _ = await _person(db, "inventory.view", "cycle_count.view", "cycle_count.create")
        wh, p, task = await _count_setup(db, s)
        await db.commit()
        ids = dict(wh=wh.id, p=p.id, task=task.id)

    body = {"task_id": str(ids["task"]), "product_id": str(ids["p"]), "counted_qty": "99", "unit": "PCS"}
    async with _client(counter) as c:
        rs = await asyncio.gather(*[c.post("/api/v1/cycle-count/entries", json=body) for _ in range(4)])
    codes = sorted(r.status_code for r in rs)
    assert codes == [201, 400, 400, 400], [r.text for r in rs]
    async with AsyncSessionLocal() as db:
        assert await _qty(db, warehouse_id=ids["wh"], product_id=ids["p"]) == Decimal("99")      # posted once
        n = (await db.execute(select(func.count()).select_from(CountEntry).where(CountEntry.task_id == ids["task"]))).scalar_one()
        moves = (await db.execute(select(func.count()).select_from(StockMovement).where(StockMovement.product_id == ids["p"]))).scalar_one()
        assert (n, moves) == (1, 1)


async def test_transfer_replay_checks_the_lot():
    from app.db.session import AsyncSessionLocal
    from app.models.inventory import Lot
    from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType

    _guard_db()
    s = uuid.uuid4().hex[:8]
    async with AsyncSessionLocal() as db:
        clerk, _ = await _person(db, "inventory.view", "inventory.transfer_all")
        a = Warehouse(code=f"M48-R8-A-{s}", name=f"POVU FG Nairobi {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        b = Warehouse(code=f"M48-R8-B-{s}", name=f"POVU FG Machakos {s}", warehouse_type=WarehouseType.FINISHED_GOODS)
        p = Product(sku=f"POVU-ALC-1L-{s}", barcode=_barcode(s), name=f"POVU AllClean 1 L {s}",
                    category=ProductCategory.HOUSEHOLD, uom=UnitOfMeasure.PCS)
        db.add_all([a, b, p])
        await db.flush()
        l1, l2 = Lot(lot_number=f"ALC-A-{s}", product_id=p.id), Lot(lot_number=f"ALC-B-{s}", product_id=p.id)
        db.add_all([l1, l2])
        await db.flush()
        await _stock_row(db, a.id, p.id, "20", l1.id)
        await _stock_row(db, a.id, p.id, "20", l2.id)
        await db.commit()
        ids = dict(a=a.id, b=b.id, p=p.id, l1=l1.id, l2=l2.id)

    key = f"povu-{uuid.uuid4()}"

    def move(lot):
        return {"product_id": str(ids["p"]), "from_warehouse_id": str(ids["a"]), "to_warehouse_id": str(ids["b"]),
                "quantity": "5", "reference": f"M48-TRF-{s}", "lot_number": lot, "idempotency_key": key}

    url = "/api/v1/inventory/stock/transfer"
    async with _client(clerk) as c:
        first = await c.post(url, json=move(f"ALC-A-{s}"))
        assert first.status_code == 201, first.text
        other_lot = await c.post(url, json=move(f"ALC-B-{s}"))                       # same key, other lot
        assert other_lot.status_code == 409, other_lot.text
        again = await c.post(url, json=move(f"ALC-A-{s}"))
        assert again.status_code == 201 and again.json()["id"] == first.json()["id"]
    async with AsyncSessionLocal() as db:
        assert await _qty(db, warehouse_id=ids["a"], product_id=ids["p"], lot_id=ids["l1"]) == Decimal("15")
        assert await _qty(db, warehouse_id=ids["a"], product_id=ids["p"], lot_id=ids["l2"]) == Decimal("20")
