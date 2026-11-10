"""M28 — authorization guards on /traceability routes."""
import re
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.traceability import router as traceability_router
from app.core.deps import get_current_user
from app.db.session import get_db
from tests.test_m28_traceability_verification import FakeDB

PUBLIC_PATHS = {"/traceability/blockchain/public/{qr_token}"}


def _user(*codes):
    perms = [SimpleNamespace(code=c, is_active=True) for c in codes]
    return SimpleNamespace(is_superuser=False,
                           roles=[SimpleNamespace(is_active=True, permissions=perms, access_scopes=[])])


def _app(db=None) -> FastAPI:
    app = FastAPI()
    app.include_router(traceability_router, prefix="/traceability")

    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    return app


def _routes():
    for route in traceability_router.routes:
        path = "/traceability" + route.path
        if path in PUBLIC_PATHS:
            continue
        for method in route.methods:
            yield method, re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)


@pytest.mark.parametrize("method,path", list(_routes()))
def test_every_non_public_route_requires_authentication(method, path):
    with TestClient(_app()) as client:
        response = client.request(method, path)
    assert response.status_code == 401, (method, path, response.status_code)


def test_view_only_user_cannot_initiate_or_close_recall():
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _user("quality.view")
    rid = uuid.uuid4()
    with TestClient(app) as client:
        initiate = client.post("/traceability/recalls", json={})
        contain = client.post(f"/traceability/recalls/{rid}/contain")
        close = client.post(f"/traceability/recalls/{rid}/close")
        report = client.get(f"/traceability/recalls/{rid}/regulatory-report")
        record = client.post("/traceability/events", json={})
    assert [r.status_code for r in (initiate, contain, close, report, record)] == [403] * 5


def test_recall_initiator_still_needs_close_permission():
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _user("traceability.recall_initiate")
    with TestClient(app) as client:
        response = client.post(f"/traceability/recalls/{uuid.uuid4()}/close")
    assert response.status_code == 403


def test_user_without_trace_permission_cannot_view():
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _user("sales.view")
    with TestClient(app) as client:
        response = client.get(f"/traceability/forward/{uuid.uuid4()}")
    assert response.status_code == 403


def test_viewer_can_export_timeline_csv():
    app = _app(FakeDB())
    app.dependency_overrides[get_current_user] = lambda: _user("traceability.view_all")
    lot_id = uuid.uuid4()
    with TestClient(app) as client:
        response = client.get(f"/traceability/timeline/{lot_id}/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert f"trace_timeline_{lot_id}.csv" in response.headers["content-disposition"]
    assert response.text.splitlines()[0].startswith("event_datetime,event_type")


def test_public_qr_route_stays_unauthenticated():
    assert len(list(_routes())) >= 38
    with TestClient(_app(FakeDB())) as client:
        response = client.get("/traceability/blockchain/public/unknown-token")
    assert response.status_code == 404
