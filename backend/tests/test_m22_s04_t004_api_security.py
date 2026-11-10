"""Focused M22 security regressions for subcontracting and routed operations."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.v1.endpoints import production_advanced, subcontracting
from app.core.deps import get_current_user
from app.db.session import get_db


def _unauthenticated_app() -> FastAPI:
    app = FastAPI()
    app.include_router(subcontracting.router, prefix="/subcontracting")
    app.include_router(production_advanced.router, prefix="/production-adv")

    async def empty_db():
        yield None

    app.dependency_overrides[get_db] = empty_db
    return app


def test_subcontracting_routes_require_authenticated_procurement_user():
    app = _unauthenticated_app()
    with TestClient(app) as client:
        responses = [
            client.get("/subcontracting/dashboard"),
            client.get("/subcontracting/orders"),
            client.post(f"/subcontracting/orders/{uuid4()}/approve"),
            client.post(f"/subcontracting/orders/{uuid4()}/complete"),
            client.post("/subcontracting/ai/run"),
        ]
    assert [response.status_code for response in responses] == [401] * len(responses)


def test_subcontracting_routes_reject_authenticated_user_without_procurement_view():
    app = _unauthenticated_app()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(), is_superuser=False, roles=[], access_scopes=[]
    )
    with TestClient(app) as client:
        response = client.get("/subcontracting/orders")
    assert response.status_code == 403


def test_subcontracting_mutation_requires_action_permission_even_with_read_access():
    app = _unauthenticated_app()
    view = SimpleNamespace(code="procurement.view", is_active=True)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(),
        is_superuser=False,
        roles=[SimpleNamespace(is_active=True, permissions=[view], access_scopes=[])],
        access_scopes=[],
    )
    with TestClient(app) as client:
        response = client.post(f"/subcontracting/orders/{uuid4()}/approve")
    assert response.status_code == 403


def test_production_work_order_read_accepts_existing_broad_view_permission():
    permission = SimpleNamespace(code="production.view", is_active=True)
    user = SimpleNamespace(
        is_superuser=False,
        roles=[SimpleNamespace(is_active=True, permissions=[permission], access_scopes=[])],
        access_scopes=[],
    )
    parent = SimpleNamespace(source_warehouse_id=uuid4(), target_warehouse_id=None)
    production_advanced._require_canonical_order_action(user, parent, "view")


def test_linking_work_order_to_subcontract_requires_production_scope():
    parent = SimpleNamespace(source_warehouse_id=uuid4(), target_warehouse_id=None)
    user = SimpleNamespace(is_superuser=False, roles=[], access_scopes=[])
    with pytest.raises(HTTPException) as denied:
        subcontracting._require_production_work_order_edit(user, parent)
    assert denied.value.status_code == 403


class _FakeDB:
    def __init__(self, parent):
        self.parent = parent

    async def get(self, model, _identity):
        return self.parent


@pytest.mark.asyncio
async def test_work_order_read_and_genealogy_require_parent_production_view(monkeypatch):
    work_order = SimpleNamespace(id=uuid4(), production_order_id=uuid4())
    parent = SimpleNamespace(source_warehouse_id=uuid4(), target_warehouse_id=None)
    user = SimpleNamespace(is_superuser=False, roles=[], access_scopes=[])
    db = _FakeDB(parent)

    async def get_work_order(_db, _pk):
        return work_order

    async def list_genealogy(_db, _pk):
        raise AssertionError("Genealogy must not be queried before authorization succeeds")

    monkeypatch.setattr(production_advanced.crud, "get_work_order", get_work_order)
    monkeypatch.setattr(production_advanced.crud, "list_work_order_genealogy", list_genealogy)

    with pytest.raises(HTTPException) as read_denied:
        await production_advanced.get_work_order(work_order.id, db, user)
    assert getattr(read_denied.value, "status_code", None) == 403

    with pytest.raises(HTTPException) as genealogy_denied:
        await production_advanced.get_work_order_genealogy(work_order.id, db, user)
    assert getattr(genealogy_denied.value, "status_code", None) == 403


@pytest.mark.asyncio
async def test_work_order_patch_locks_and_authorizes_parent_before_mutation(monkeypatch):
    work_order = SimpleNamespace(id=uuid4(), production_order_id=uuid4())
    parent = SimpleNamespace(source_warehouse_id=uuid4(), target_warehouse_id=None)
    user = SimpleNamespace(is_superuser=False, roles=[], access_scopes=[])
    db = _FakeDB(parent)

    async def lock_context(_db, _pk):
        return parent, work_order

    async def should_not_update(*_args):
        raise AssertionError("Work-order mutation must not run before authorization")

    monkeypatch.setattr(production_advanced.crud, "_lock_work_order_context", lock_context)
    monkeypatch.setattr(production_advanced.crud, "update_work_order", should_not_update)

    with pytest.raises(HTTPException) as denied:
        await production_advanced.update_work_order(
            work_order.id,
            production_advanced.WorkOrderUpdate(notes="unauthorized"),
            db,
            user,
        )
    assert getattr(denied.value, "status_code", None) == 403
