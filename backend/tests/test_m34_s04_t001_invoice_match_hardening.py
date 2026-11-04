"""Focused authorization and pure matching checks for M34.S04.T001."""
from __future__ import annotations

from types import SimpleNamespace
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import invoice_match
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.invoice_match import MatchLineStatus, InvoiceMatchTolerance
from app.services.invoice_match_service import _evaluate_line_status


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(invoice_match.router, prefix="/invoice-match")

    async def empty_db():
        yield None

    app.dependency_overrides[get_db] = empty_db
    return app


def _user(
    *permission_codes: str,
    email: str = "finance@example.invalid",
    role_name: str = "finance_manager",
):
    permissions = [
        SimpleNamespace(code=code, is_active=True)
        for code in permission_codes
    ]
    role = SimpleNamespace(name=role_name, is_active=True, permissions=permissions)
    return SimpleNamespace(is_superuser=False, roles=[role], email=email)


def _dependency_tree_has(dependant, target) -> bool:
    return dependant.call is target or any(
        _dependency_tree_has(child, target)
        for child in dependant.dependencies
    )


def test_every_invoice_match_route_requires_the_authenticated_user_dependency():
    routes = [route for route in invoice_match.router.routes if hasattr(route, "dependant")]
    assert routes
    assert all(_dependency_tree_has(route.dependant, get_current_user) for route in routes)


def test_invoice_match_read_and_write_routes_reject_anonymous_requests():
    app = _app()
    with TestClient(app) as client:
        read = client.get("/invoice-match/dashboard")
        run = client.post(
            "/invoice-match/run",
            json={"invoice_id": str(uuid4())},
        )
        review = client.post(
            f"/invoice-match/{uuid4()}/approve-exception",
            json={
                "justification": "synthetic",
                "expected_run_at": "2026-11-04T00:00:00",
            },
        )
    assert read.status_code == 401
    assert run.status_code == 401
    assert review.status_code == 401


def test_finance_view_permission_cannot_run_a_match():
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _user("finance.view")
    with TestClient(app) as client:
        response = client.post(
            "/invoice-match/run",
            json={"invoice_id": str(uuid4())},
        )
    assert response.status_code == 403


def test_finance_view_permission_cannot_review_or_change_tolerance_rules():
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _user("finance.view")
    expected_run_at = datetime(2026, 11, 4)
    with TestClient(app) as client:
        review = client.post(
            f"/invoice-match/{uuid4()}/review",
            json={
                "action": "APPROVED_EXCEPTION",
                "reviewer_name": "untrusted request value",
                "expected_run_at": expected_run_at.isoformat(),
            },
        )
        configure = client.post(
            "/invoice-match/tolerance-rules",
            json={"rule_name": "synthetic unauthorized rule"},
        )

    assert review.status_code == 403
    assert configure.status_code == 403


def test_tolerance_rules_route_is_reachable_for_finance_viewer(monkeypatch):
    app = _app()
    app.dependency_overrides[get_current_user] = lambda: _user("finance.view")

    async def no_rules(_db, active_only=False):
        return []

    monkeypatch.setattr(invoice_match.svc, "list_tolerance_rules", no_rules)
    with TestClient(app) as client:
        response = client.get("/invoice-match/tolerance-rules")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_review_audit_actor_comes_from_authenticated_user(monkeypatch):
    captured = {}

    async def fake_submit_review(_db, header_id, payload, **kwargs):
        captured["header_id"] = header_id
        captured["payload"] = payload
        captured["actor_role_names"] = kwargs["actor_role_names"]
        return object()

    monkeypatch.setattr(invoice_match.svc, "submit_review", fake_submit_review)
    header_id = uuid4()
    body = invoice_match.ReviewCreate(
        action="APPROVED_EXCEPTION",
        reviewer_name="invented caller name",
        reviewer_role="invented role",
        justification="synthetic test reason",
        expected_run_at=datetime(2026, 11, 4),
    )

    await invoice_match.review(
        header_id,
        body,
        db=None,
        current_user=_user("finance.approve", email="actual.actor@example.invalid"),
    )

    assert captured["header_id"] == header_id
    assert captured["payload"].reviewer_name == "actual.actor@example.invalid"
    assert captured["payload"].reviewer_role is None
    assert captured["actor_role_names"] == {"finance_manager"}


def test_tax_variance_inside_configured_tolerance_is_not_labeled_exact():
    po_line = SimpleNamespace()
    grn_line = SimpleNamespace()
    rule = InvoiceMatchTolerance(
        rule_name="synthetic tax tolerance",
        quantity_tolerance_pct=1,
        price_tolerance_pct=2,
        tax_tolerance_pct=0.2,
    )

    status = _evaluate_line_status(
        po_line=po_line,
        grn_lines=[grn_line],
        invoiced_qty=10,
        billable_qty=10,
        qty_var_pct=0,
        price_var_pct=0,
        tax_var=0.001,
        rule=rule,
    )
    assert status == MatchLineStatus.MATCHED_WITHIN_TOLERANCE
