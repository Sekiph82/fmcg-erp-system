"""M17.S02.T005 — every GraphQL query executes against PostgreSQL (disposable database)."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from graphql import graphql
from sqlalchemy import func, select

from app.api.v1.endpoints.graphql_api import SCHEMA, graphql_context
from app.db.session import AsyncSessionLocal, engine
from app.models.inventory import Stock, StockType
from app.models.master import Product, ProductCategory, UnitOfMeasure, Warehouse, WarehouseType

TASK_DB_ENV = "M17_S02_T005_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M17_S02_T005_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m17_s02_t005_[a-f0-9]{24}")

pytestmark = pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires the task-owned disposable PostgreSQL")

ADMIN = SimpleNamespace(id=uuid4(), is_superuser=True, roles=[])


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_all_queries_run_on_postgresql():
    s = uuid4().hex[:10]
    async with AsyncSessionLocal() as db:
        assert engine.url.host in {"127.0.0.1", "localhost", "::1"} and engine.url.password is None
        assert TASK_DB_PATTERN.fullmatch(os.environ.get(TASK_DB_NAME_ENV, ""))
        assert (await db.execute(select(func.current_database()))).scalar_one() == os.environ[TASK_DB_NAME_ENV]
        product = Product(sku=f"GQL-{s}", name=f"Synthetic GraphQL product {s}", category=ProductCategory.FOOD,
                          uom=UnitOfMeasure.KG)
        warehouse = Warehouse(code=f"GQL-W-{s}", name="Synthetic GraphQL warehouse", warehouse_type=WarehouseType.FINISHED_GOODS)
        db.add_all([product, warehouse])
        await db.flush()
        db.add(Stock(stock_type=StockType.PRODUCT, warehouse_id=warehouse.id, product_id=product.id,
                     quantity_on_hand=Decimal("12.5"), quantity_reserved=Decimal("0"), quantity_available=Decimal("12.5")))
        await db.commit()
        query = f"""{{
          products(search: "GQL-{s}") {{ sku name uom }}
          materials(limit: 1) {{ code }}
          suppliers(limit: 1) {{ code }}
          customers(limit: 1) {{ code }}
          salesOrders(dateFrom: "{date.today().isoformat()}", limit: 1) {{ orderNo }}
          purchaseOrders(limit: 1) {{ poNo }}
          productionOrders(limit: 1) {{ orderNo }}
          inventoryLevels(sku: "GQL-{s}") {{ warehouseId quantityOnHand quantityAvailable isBlocked }}
        }}"""
        result = await graphql(SCHEMA, query, context_value=graphql_context(db, ADMIN))
        assert result.errors is None, result.errors
        assert result.data["products"] == [{"sku": f"GQL-{s}", "name": f"Synthetic GraphQL product {s}", "uom": "KG"}]
        assert result.data["inventoryLevels"] == [{"warehouseId": str(warehouse.id), "quantityOnHand": 12.5,
                                                   "quantityAvailable": 12.5, "isBlocked": False}]
