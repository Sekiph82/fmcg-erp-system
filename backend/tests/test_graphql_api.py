"""Read-only GraphQL API: queries, permission parity with REST, mutation and depth limits."""
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.graphql_api import router
from app.core.deps import get_current_user, get_db
from app.models.master import Product, ProductCategory, UnitOfMeasure, Supplier
from app.models.sales import SalesOrder, SOStatus
from fake_async_db import FakeDB


def _user(*codes):
    perms = [SimpleNamespace(code=c, is_active=True) for c in codes]
    return SimpleNamespace(id=uuid.uuid4(), is_superuser=False, full_name="u", username="u", email="u@example.invalid",
                           roles=[SimpleNamespace(is_active=True, permissions=perms, access_scopes=[])])


@pytest.fixture
def env():
    db = FakeDB()
    db.add(Product(id=uuid.uuid4(), sku="SKU-1", name="Synthetic juice", category=ProductCategory.BEVERAGE,
                   uom=UnitOfMeasure.PCS, is_active=True))
    db.add(Product(id=uuid.uuid4(), sku="SKU-2", name="Synthetic water", category=ProductCategory.BEVERAGE,
                   uom=UnitOfMeasure.PCS, is_active=True))
    db.add(Supplier(id=uuid.uuid4(), code="SUP-1", name="Synthetic supplier", is_active=True))
    app = FastAPI()
    app.include_router(router, prefix="/graphql")

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db

    def as_(user):
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    return db, as_


def _q(client, query, variables=None):
    r = client.post("/graphql", json={"query": query, "variables": variables})
    return r.status_code, r.json()


def test_products_query_with_pagination(env):
    _, as_ = env
    status, body = _q(as_(_user()), "{ products(limit: 1) { sku name category uom isActive } }")
    assert status == 200 and "errors" not in body
    assert body["data"]["products"] == [{"sku": "SKU-1", "name": "Synthetic juice", "category": "BEVERAGE",
                                         "uom": "PCS", "isActive": True}]
    _, body = _q(as_(_user()), "query($n: Int) { products(limit: $n, offset: 1) { sku } }", {"n": 5})
    assert body["data"]["products"] == [{"sku": "SKU-2"}]


def test_permissions_mirror_rest_and_require_company_wide_grants(env):
    _, as_ = env
    _, denied = _q(as_(_user()), "{ suppliers { code } }")
    assert "Permission required" in denied["errors"][0]["message"] and denied["data"] is None
    _, ok = _q(as_(_user("suppliers.view")), "{ suppliers { code name } }")
    assert ok["data"]["suppliers"] == [{"code": "SUP-1", "name": "Synthetic supplier"}]
    _, scoped = _q(as_(_user("sales.view", "sales.view_own_scope")), "{ salesOrders { orderNo } }")
    assert "sales.view_all" in scoped["errors"][0]["message"]


def test_sales_orders_filter(env):
    db, as_ = env
    from datetime import date
    db.add(SalesOrder(id=uuid.uuid4(), order_no="SO-1", customer_id=uuid.uuid4(), order_date=date(2026, 10, 1),
                      status=SOStatus.CONFIRMED))
    db.add(SalesOrder(id=uuid.uuid4(), order_no="SO-2", customer_id=uuid.uuid4(), order_date=date(2026, 11, 1),
                      status=SOStatus.DRAFT))
    _, body = _q(as_(_user("sales.view_all")), '{ salesOrders(status: "CONFIRMED") { orderNo status orderDate } }')
    assert body["data"]["salesOrders"] == [{"orderNo": "SO-1", "status": "CONFIRMED", "orderDate": "2026-10-01"}]


def test_mutations_depth_and_invalid_queries_are_refused(env):
    _, as_ = env
    c = as_(_user())
    assert c.post("/graphql", json={"query": "mutation { x }"}).status_code == 400
    _, invalid = _q(c, "{ products { password } }")
    assert "Cannot query field 'password'" in invalid["errors"][0]["message"]
    deep = "{ products { " + "__typename " + "} }"
    assert c.post("/graphql", json={"query": deep}).status_code == 200
    nested = "{ " + "__schema { types { fields { type { ofType { ofType { ofType { name } } } } } } }" + " }"
    assert c.post("/graphql", json={"query": nested}).status_code == 400
    assert c.post("/graphql", json={"query": "x" * 10_001}).status_code == 422
