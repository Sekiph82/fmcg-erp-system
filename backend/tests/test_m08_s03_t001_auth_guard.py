"""Authorization checks for the M08 production transition endpoints."""
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.db.session import get_db
from app.api.v1.endpoints.production_execution import (
    _require_execution_action,
    _require_scope_change,
    router as production_execution_router,
)


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(production_execution_router, prefix="/production-execution")

    async def empty_db():
        yield None

    app.dependency_overrides[get_db] = empty_db
    return app


def test_state_transition_endpoints_require_an_authenticated_user():
    app = _app()
    with TestClient(app) as client:
        order_response = client.post(f"/production-execution/{uuid4()}/release")
        work_order_response = client.post(f"/production-execution/work-orders/{uuid4()}/start")
        material_response = client.post(
            f"/production-execution/{uuid4()}/materials",
            json={"required_qty": "1", "uom": "KG"},
        )
        material_id = str(uuid4())
        issue_response = client.post(
            f"/production-execution/{uuid4()}/materials/issue",
            json={"material_id": material_id, "qty": "1", "action": "issue"},
        )
        return_response = client.post(
            f"/production-execution/{uuid4()}/materials/return",
            json={"material_id": material_id, "qty": "1", "action": "return"},
        )
        genealogy_response = client.post(
            f"/production-execution/{uuid4()}/genealogy",
            json={"link_type": "INPUT_OUTPUT"},
        )
        ai_response = client.post(f"/production-execution/{uuid4()}/run-ai")
        ai_action_response = client.post(
            f"/production-execution/ai-recs/{uuid4()}/action",
            json={"status": "ACCEPTED"},
        )
        dashboard_response = client.get("/production-execution/dashboard")

    assert order_response.status_code == 401
    assert work_order_response.status_code == 401
    assert material_response.status_code == 401
    assert issue_response.status_code == 401
    assert return_response.status_code == 401
    assert genealogy_response.status_code == 401
    assert ai_response.status_code == 401
    assert ai_action_response.status_code == 401
    assert dashboard_response.status_code == 401


def test_create_permission_denial_remains_forbidden_http_status():
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_superuser=False, roles=[])
    with TestClient(app) as client:
        response = client.post(
            "/production-execution",
            json={"planned_qty": "10", "uom": "KG"},
        )
    assert response.status_code == 403


def test_scoped_production_permission_is_required_for_transition():
    permission = SimpleNamespace(code="production.release_own_scope", is_active=True)
    scope = SimpleNamespace(
        scope_type="production_line",
        scope_id="line-a",
        is_active=True,
        can_release=True,
    )
    user = SimpleNamespace(
        is_superuser=False,
        roles=[SimpleNamespace(is_active=True, permissions=[permission], access_scopes=[scope])],
    )
    record = SimpleNamespace(plant_id=None, section_id=None, line_id="line-a")

    _require_execution_action(user, "release", record)

    other_line = SimpleNamespace(plant_id=None, section_id=None, line_id="line-b")
    try:
        _require_execution_action(user, "release", other_line)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("A scoped production user must not transition a different line's order")


def test_scoped_user_cannot_move_work_to_an_unassigned_line():
    permission = SimpleNamespace(code="production.edit_own_scope", is_active=True)
    scope = SimpleNamespace(
        scope_type="production_line",
        scope_id="line-a",
        is_active=True,
        can_edit=True,
    )
    user = SimpleNamespace(
        is_superuser=False,
        roles=[SimpleNamespace(is_active=True, permissions=[permission], access_scopes=[scope])],
    )
    current = SimpleNamespace(plant_id=None, section_id=None, line_id="line-a")

    try:
        _require_scope_change(user, "edit", current, {"line_id": "line-b"})
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("A scoped production user must not reassign work into another line")


def test_unchanged_authorized_scope_cannot_mask_a_different_scope_change():
    permission = SimpleNamespace(code="production.edit_own_scope", is_active=True)
    scope = SimpleNamespace(
        scope_type="section",
        scope_id="section-a",
        is_active=True,
        can_edit=True,
    )
    user = SimpleNamespace(
        is_superuser=False,
        roles=[SimpleNamespace(is_active=True, permissions=[permission], access_scopes=[scope])],
    )
    current = SimpleNamespace(plant_id="plant-a", section_id="section-a", line_id=None)

    try:
        _require_scope_change(user, "edit", current, {"plant_id": "plant-b"})
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("An unchanged section grant must not authorize moving an order to another plant")
