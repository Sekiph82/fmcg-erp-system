"""M28.S04.T003 — deep genealogy trace performance on a disposable PostgreSQL database.

Measures backward trace over a 300-lot chain and forward trace over a 1 → 20 → 400 fan-out,
counting SQL statements so the per-node query cost is visible. Thresholds are generous
regression guards for a local container, not production SLAs.
"""
from __future__ import annotations

import os
import re
import time
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event, func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Lot
from app.models.master import Product, ProductCategory, UnitOfMeasure
from app.models.traceability import GenealogyRelType, LotGenealogyLink
from app.services import traceability_service

TASK_DB_ENV = "M28_S04_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M28_S04_T003_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m28_s04_t003_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


class _StatementCounter:
    def __init__(self):
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1


async def _setup(db, s):
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
    expected = os.environ.get(TASK_DB_NAME_ENV, "")
    assert TASK_DB_PATTERN.fullmatch(expected)
    assert (await db.execute(select(func.current_database()))).scalar_one() == expected
    product = Product(sku=f"M28P-{s}", name=f"Synthetic genealogy product {s}", category=ProductCategory.FOOD,
                      uom=UnitOfMeasure.KG)
    db.add(product)
    await db.flush()
    return product.id


def _lots(product_id, prefix, n):
    return [Lot(product_id=product_id, lot_number=f"{prefix}-{i}") for i in range(n)]


@pytest.mark.asyncio
async def test_deep_chain_backward_and_wide_forward_trace_on_postgresql():
    s = uuid4().hex[:12]
    async with AsyncSessionLocal() as db:
        product_id = await _setup(db, s)
        chain = _lots(product_id, f"CH-{s}", 300)
        root = Lot(product_id=product_id, lot_number=f"ROOT-{s}")
        mid = _lots(product_id, f"MID-{s}", 20)
        leaves = _lots(product_id, f"LEAF-{s}", 400)
        db.add_all(chain + [root] + mid + leaves)
        await db.flush()
        links = [LotGenealogyLink(parent_lot_id=p.id, child_lot_id=c.id, relationship_type=GenealogyRelType.prepared_from)
                 for p, c in zip(chain, chain[1:])]
        links += [LotGenealogyLink(parent_lot_id=root.id, child_lot_id=m.id, relationship_type=GenealogyRelType.bulk_from)
                  for m in mid]
        links += [LotGenealogyLink(parent_lot_id=mid[i % 20].id, child_lot_id=leaf.id,
                                   relationship_type=GenealogyRelType.packed_from) for i, leaf in enumerate(leaves)]
        db.add_all(links)
        await db.commit()
        tail_id, root_id, leaf_ids = chain[-1].id, root.id, {leaf.id for leaf in leaves}

    counter = _StatementCounter()
    event.listen(engine.sync_engine, "before_cursor_execute", counter)
    try:
        async with AsyncSessionLocal() as db:
            start = time.perf_counter()
            backward = await traceability_service.backward_trace(db, tail_id, max_depth=400)
            backward_secs = time.perf_counter() - start
            backward_statements = counter.count

            counter.count = 0
            start = time.perf_counter()
            forward = await traceability_service.forward_trace(db, root_id, max_depth=5)
            forward_secs = time.perf_counter() - start
            forward_statements = counter.count
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", counter)

    print(f"\nM28 deep genealogy on PostgreSQL: backward 300-lot chain {backward_secs:.2f}s / {backward_statements} SQL; "
          f"forward 1->20->400 fan-out {forward_secs:.2f}s / {forward_statements} SQL")
    assert len(backward.source_lots) == 299 and backward.genealogy_depth == 299
    forward_ids = {UUID(str(row["lot_id"])) for row in forward.affected_lots}
    assert leaf_ids <= forward_ids and len(forward_ids) == 420
    assert backward_secs < 30 and forward_secs < 30
