"""M34.S05.T001: persisted RFQ sourcing workflow from invitation to award."""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.engine import URL

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.master import Supplier
from app.models.procurement import (
    ProcurementApprovalDocumentType,
    ProcurementApprovalRule,
    RFQAward,
    RFQAwardAllocation,
    RFQAwardApproval,
    RFQAwardApprovalStatus,
    RFQAwardStatus,
    RFQEvaluationStatus,
    RFQInvitationStatus,
    RFQRequest,
    RFQResponse,
    RFQResponseEvaluation,
    RFQResponseStatus,
    RFQStatus,
)
from app.models.two_factor import TwoFAMethod, User2FASettings
from app.models.user import User


TASK_DB_ENV = "M34_S05_T001_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S05_T001_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s05_t001_[a-f0-9]{24}")


def _is_task_database(url, expected_name: str | None) -> bool:
    return bool(
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and TASK_DB_PATTERN.fullmatch(expected_name)
        and url.database == expected_name
    )


def _require_task_database() -> None:
    expected_name = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1":
        pytest.skip(f"Run only with {TASK_DB_ENV}=1 for this task-owned disposable PostgreSQL database.")
    if not _is_task_database(engine.url, expected_name):
        pytest.fail("Refusing integration writes: DATABASE_URL must match this task's exact passwordless loopback database.")


def _evaluation(criterion_by_code: dict[str, dict], technical_pass: bool) -> dict:
    return {
        "evaluations": [
            {
                "criterion_id": criterion_by_code["TECHNICAL_FIT"]["id"],
                "score": "88.00" if technical_pass else "40.00",
                "passes_gate": technical_pass,
                "comments": "Synthetic mandatory technical gate.",
            },
            {
                "criterion_id": criterion_by_code["COMMERCIAL_VALUE"]["id"],
                "score": "75.00",
                "comments": "Synthetic commercial score.",
            },
        ]
    }


def _auth_cookies(user: User) -> dict[str, str]:
    return {
        settings.AUTH_COOKIE_NAME: create_access_token(
            str(user.id), session_version=user.auth_session_version
        )
    }


def test_database_guard_rejects_non_task_targets():
    name = "fmcg_m34_s05_t001_0123456789abcdef01234567"
    assert _is_task_database(URL.create("postgresql+asyncpg", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.invalid", database=name), name)
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", password="secret", host="127.0.0.1", database=name),
        name,
    )
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires this task's disposable PostgreSQL database")
async def test_sourcing_event_runs_from_invitation_through_governed_award(monkeypatch):
    _require_task_database()
    monkeypatch.setattr(settings, "SECRET_KEY", "M34-S05-T001-SYNTHETIC-TEST-SECRET-KEY-ONLY")
    suffix = uuid4().hex[:16]
    requester = User(
        email=f"m34-s05-requester-{suffix}@example.invalid",
        username=f"m34s05r{suffix}",
        full_name="Synthetic sourcing requester",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    first_approver = User(
        email=f"m34-s05-approver1-{suffix}@example.invalid",
        username=f"m34s05a1{suffix}",
        full_name="Synthetic first approver",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    second_approver = User(
        email=f"m34-s05-approver2-{suffix}@example.invalid",
        username=f"m34s05a2{suffix}",
        full_name="Synthetic second approver",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    invited_suppliers = [
        Supplier(code=f"M34S05-{suffix}-A", name="Synthetic invited supplier A", is_active=True),
        Supplier(code=f"M34S05-{suffix}-B", name="Synthetic invited supplier B", is_active=True),
    ]
    uninvited_supplier = Supplier(
        code=f"M34S05-{suffix}-X", name="Synthetic uninvited supplier", is_active=True
    )
    rfq_id = None
    app_transport = ASGITransport(app=app)

    async with AsyncSessionLocal() as db:
        db.add_all([requester, first_approver, second_approver, *invited_suppliers, uninvited_supplier])
        await db.flush()
        requester_id = requester.id
        first_approver_id = first_approver.id
        second_approver_id = second_approver.id
        supplier_a_id, supplier_b_id = (supplier.id for supplier in invited_suppliers)
        uninvited_supplier_id = uninvited_supplier.id
        db.add_all(
            [
                User2FASettings(
                    user_id=user_id,
                    is_enabled=True,
                    method=TwoFAMethod.TOTP,
                    secret_key=f"SYNTHETIC-{suffix}-{index}",
                )
                for index, user_id in enumerate(
                    [requester_id, first_approver_id, second_approver_id], start=1
                )
            ]
        )
        await db.commit()

        try:
            async with AsyncClient(
                transport=app_transport,
                base_url="http://m34-s05.test",
            ) as anonymous_client:
                unauthenticated = await anonymous_client.post(
                    "/api/v1/procurement/rfq/",
                    json={
                        "rfq_no": f"M34-S05-UNAUTH-{suffix}",
                        "title": "Unauthenticated synthetic request",
                        "quantity": "1.000",
                        "supplier_ids": [str(supplier_a_id)],
                    },
                )
                assert unauthenticated.status_code == 401

            async with AsyncClient(
                transport=app_transport,
                base_url="http://m34-s05.test",
                cookies=_auth_cookies(requester),
            ) as requester_client:
                create_response = await requester_client.post(
                    "/api/v1/procurement/rfq/",
                    json={
                        "rfq_no": f"M34-S05-{suffix}",
                        "title": "Synthetic sourcing workflow acceptance",
                        "quantity": "10.000",
                        "unit": "KG",
                        "response_deadline": (date.today() + timedelta(days=5)).isoformat(),
                        "supplier_ids": [str(supplier_a_id), str(supplier_b_id)],
                    },
                )
                assert create_response.status_code == 201, create_response.text
                draft = create_response.json()
                rfq_id = UUID(draft["id"])
                assert draft["status"] == RFQStatus.DRAFT.value
                assert {row["supplier_id"] for row in draft["responses"]} == {
                    str(supplier_a_id), str(supplier_b_id)
                }
                assert all(row["invitation_status"] == RFQInvitationStatus.PENDING.value for row in draft["responses"])

                issued_response = await requester_client.post(
                    f"/api/v1/procurement/rfq/{rfq_id}/issue-invitations"
                )
                assert issued_response.status_code == 200, issued_response.text
                issued = issued_response.json()
                assert issued["status"] == RFQStatus.SENT.value
                assert len(issued["responses"]) == 2
                assert all(
                    row["invitation_status"] == RFQInvitationStatus.ISSUED.value
                    and row["invitation_issued_at"] is not None
                    for row in issued["responses"]
                )
                repeated_issue = await requester_client.post(
                    f"/api/v1/procurement/rfq/{rfq_id}/issue-invitations"
                )
                assert repeated_issue.status_code == 409

                matrix_response = await requester_client.post(
                    f"/api/v1/procurement/rfq/{rfq_id}/evaluation-matrix",
                    json={
                        "criteria": [
                            {
                                "code": "TECHNICAL_FIT",
                                "name": "Technical fit",
                                "dimension": "TECHNICAL",
                                "weight_percent": "60.00",
                                "is_mandatory": True,
                            },
                            {
                                "code": "COMMERCIAL_VALUE",
                                "name": "Commercial value",
                                "dimension": "COMMERCIAL",
                                "weight_percent": "40.00",
                                "is_mandatory": False,
                            },
                        ]
                    },
                )
                assert matrix_response.status_code == 200, matrix_response.text
                criteria = matrix_response.json()
                criterion_by_code = {row["code"]: row for row in criteria}
                assert set(criterion_by_code) == {"TECHNICAL_FIT", "COMMERCIAL_VALUE"}

                uninvited_bid = await requester_client.post(
                    f"/api/v1/procurement/rfq/{rfq_id}/responses",
                    json={
                        "supplier_id": str(uninvited_supplier_id),
                        "quoted_unit_price": "3.5000",
                        "quoted_currency": "KES",
                        "lead_time_days": 4,
                    },
                )
                assert uninvited_bid.status_code == 403

                bid_responses = []
                for supplier_id, unit_price, lead_time in (
                    (supplier_a_id, "3.2500", 4),
                    (supplier_b_id, "3.0000", 5),
                ):
                    bid_response = await requester_client.post(
                        f"/api/v1/procurement/rfq/{rfq_id}/responses",
                        json={
                            "supplier_id": str(supplier_id),
                            "quoted_unit_price": unit_price,
                            "quoted_currency": "KES",
                            "lead_time_days": lead_time,
                            "valid_until": (date.today() + timedelta(days=10)).isoformat(),
                        },
                    )
                    assert bid_response.status_code == 201, bid_response.text
                    bid_responses.append(bid_response.json())
                bid_a, bid_b = bid_responses
                assert bid_a["status"] == bid_b["status"] == RFQResponseStatus.SUBMITTED.value
                assert bid_a["submitted_by_id"] == bid_b["submitted_by_id"] == str(requester_id)

                async def submit_evaluation(response_id: str, technical_pass: bool):
                    return await requester_client.put(
                        f"/api/v1/procurement/rfq/{rfq_id}/responses/{response_id}/evaluations",
                        json=_evaluation(criterion_by_code, technical_pass),
                    )

                evaluation_a = await submit_evaluation(bid_a["id"], True)
                evaluation_b_failed = await submit_evaluation(bid_b["id"], False)
                assert evaluation_a.status_code == evaluation_b_failed.status_code == 200
                assert {row["revision_no"] for row in evaluation_a.json()} == {1}
                assert {row["revision_no"] for row in evaluation_b_failed.json()} == {1}

                disqualified_award = await requester_client.post(
                    f"/api/v1/procurement/rfq/{rfq_id}/award-proposals",
                    json={
                        "allocations": [{"response_id": bid_b["id"], "quantity": "10.000"}],
                        "justification": "Synthetic disqualified bid must not be awarded.",
                    },
                )
                assert disqualified_award.status_code == 409

                evaluation_b_passed = await submit_evaluation(bid_b["id"], True)
                assert evaluation_b_passed.status_code == 200, evaluation_b_passed.text
                assert {row["revision_no"] for row in evaluation_b_passed.json()} == {1, 2}

                db.add_all(
                    [
                        ProcurementApprovalRule(
                            rule_name=f"M34 S05 synthetic approval level one {suffix}",
                            document_type=ProcurementApprovalDocumentType.RFQ,
                            approval_level=1,
                            approver_user_id=first_approver_id,
                            is_active=True,
                        ),
                        ProcurementApprovalRule(
                            rule_name=f"M34 S05 synthetic approval level two {suffix}",
                            document_type=ProcurementApprovalDocumentType.RFQ,
                            approval_level=2,
                            approver_user_id=second_approver_id,
                            is_active=True,
                        ),
                    ]
                )
                await db.commit()

                proposal_response = await requester_client.post(
                    f"/api/v1/procurement/rfq/{rfq_id}/award-proposals",
                    json={
                        "allocations": [{"response_id": bid_a["id"], "quantity": "10.000"}],
                        "justification": "Synthetic qualified bid selected after technical and commercial evaluation.",
                    },
                )
                assert proposal_response.status_code == 201, proposal_response.text
                proposal = proposal_response.json()
                award_id = proposal["id"]
                assert proposal["status"] == RFQAwardStatus.PENDING_APPROVAL.value
                assert Decimal(proposal["total_amount"]) == Decimal("32.5000000")
                assert len(proposal["allocations"]) == 1
                assert {row["approval_level"] for row in proposal["approvals"]} == {1, 2}
                pending_rfq = await db.get(RFQRequest, rfq_id)
                assert pending_rfq.status == RFQStatus.RESPONSES_RECEIVED

                async with AsyncClient(
                    transport=app_transport,
                    base_url="http://m34-s05.test",
                    cookies=_auth_cookies(second_approver),
                ) as second_approver_client:
                    wrong_approver = await second_approver_client.post(
                        f"/api/v1/procurement/rfq/{rfq_id}/awards/{award_id}/approve",
                        json={"comments": "Synthetic wrong-level attempt."},
                    )
                assert wrong_approver.status_code == 403

                first_approver_client = AsyncClient(
                    transport=app_transport,
                    base_url="http://m34-s05.test",
                    cookies=_auth_cookies(first_approver),
                )
                second_approver_client = AsyncClient(
                    transport=app_transport,
                    base_url="http://m34-s05.test",
                    cookies=_auth_cookies(second_approver),
                )
                async with first_approver_client, second_approver_client:
                    pending_response = await first_approver_client.post(
                        f"/api/v1/procurement/rfq/{rfq_id}/awards/{award_id}/approve",
                        json={"comments": "Synthetic first-level approval."},
                    )
                    assert pending_response.status_code == 200, pending_response.text
                    pending = pending_response.json()
                    assert pending["status"] == RFQAwardStatus.PENDING_APPROVAL.value
                    assert {
                        row["approval_level"]
                        for row in pending["approvals"]
                        if row["decision_status"] == RFQAwardApprovalStatus.PENDING.value
                    } == {2}

                    complete_response = await second_approver_client.post(
                        f"/api/v1/procurement/rfq/{rfq_id}/awards/{award_id}/approve",
                        json={"comments": "Synthetic second-level approval."},
                    )
                    assert complete_response.status_code == 200, complete_response.text
                    complete = complete_response.json()
                    assert complete["status"] == RFQAwardStatus.APPROVED.value
                    assert all(row["decided_by_id"] is not None and row["decided_at"] is not None for row in complete["approvals"])
                    assert {row["decision_status"] for row in complete["approvals"]} == {
                        RFQAwardApprovalStatus.APPROVED.value
                    }

                detail_response = await requester_client.get(f"/api/v1/procurement/rfq/{rfq_id}")
                assert detail_response.status_code == 200, detail_response.text
                detail = detail_response.json()
                assert detail["status"] == RFQStatus.AWARDED.value
                assert detail["awarded_supplier_id"] == str(supplier_a_id)
                response_statuses = {row["id"]: row["status"] for row in detail["responses"]}
                assert response_statuses[bid_a["id"]] == RFQResponseStatus.AWARDED.value
                assert response_statuses[bid_b["id"]] == RFQResponseStatus.REJECTED.value
                persisted_b_history = next(row for row in detail["responses"] if row["id"] == bid_b["id"])
                assert {row["revision_no"] for row in persisted_b_history["evaluation_history"]} == {1, 2}
        finally:
            await db.rollback()
            if rfq_id is not None:
                award_ids = select(RFQAward.id).where(RFQAward.rfq_id == rfq_id)
                response_ids = select(RFQResponse.id).where(RFQResponse.rfq_id == rfq_id)
                await db.execute(delete(RFQAwardApproval).where(RFQAwardApproval.award_id.in_(award_ids)))
                await db.execute(delete(RFQAwardAllocation).where(RFQAwardAllocation.award_id.in_(award_ids)))
                await db.execute(delete(RFQAward).where(RFQAward.rfq_id == rfq_id))
                await db.execute(delete(RFQResponseEvaluation).where(RFQResponseEvaluation.response_id.in_(response_ids)))
                await db.execute(delete(RFQResponse).where(RFQResponse.rfq_id == rfq_id))
                await db.execute(delete(RFQRequest).where(RFQRequest.id == rfq_id))
            await db.execute(
                delete(ProcurementApprovalRule).where(
                    ProcurementApprovalRule.approver_user_id.in_([first_approver_id, second_approver_id]),
                    ProcurementApprovalRule.rule_name.like(f"M34 S05 synthetic approval % {suffix}"),
                )
            )
            await db.execute(
                delete(Supplier).where(Supplier.id.in_([supplier_a_id, supplier_b_id, uninvited_supplier_id]))
            )
            await db.execute(delete(User).where(User.id.in_([requester_id, first_approver_id, second_approver_id])))
            await db.commit()
