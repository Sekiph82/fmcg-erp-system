"""M34.S01.T003 weighted technical/commercial bid evaluation acceptance."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.engine import URL

from app.api.v1.endpoints.procurement import (
    add_rfq_response,
    create_rfq_evaluation_matrix,
    get_rfq,
    submit_rfq_response_evaluations,
)
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Supplier
from app.models.procurement import (
    RFQEvaluationCriterion,
    RFQEvaluationDimension,
    RFQEvaluationStatus,
    RFQInvitationStatus,
    RFQRequest,
    RFQResponse,
    RFQResponseEvaluation,
    RFQResponseStatus,
    RFQStatus,
)
from app.models.user import User
from app.schemas.procurement import (
    RFQEvaluationMatrixCreate,
    RFQResponseCreate,
    RFQResponseEvaluationSubmit,
)


TASK_DB_ENV = "M34_S01_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S01_T003_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s01_t003_[a-f0-9]{24}")


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
        pytest.skip(f"Run only with {TASK_DB_ENV}=1 for the task-owned disposable PostgreSQL database.")
    if not _is_task_database(engine.url, expected_name):
        pytest.fail("Refusing integration writes: DATABASE_URL must match this task's exact passwordless loopback database.")


def _criteria():
    return [
        {"code": "TECHNICAL_FIT", "name": "Technical fit", "dimension": "TECHNICAL", "weight_percent": "60.00", "is_mandatory": True},
        {"code": "COMMERCIAL_VALUE", "name": "Commercial value", "dimension": "COMMERCIAL", "weight_percent": "40.00", "is_mandatory": False},
    ]


def test_database_guard_rejects_non_task_targets():
    name = "fmcg_m34_s01_t003_0123456789abcdef01234567"
    assert _is_task_database(URL.create("postgresql+asyncpg", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.invalid", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="erp", password="secret", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


def test_evaluation_matrix_requires_both_dimensions_unique_codes_and_exact_weights():
    valid = RFQEvaluationMatrixCreate(criteria=_criteria())
    assert sum((item.weight_percent for item in valid.criteria), Decimal("0")) == Decimal("100.00")
    assert {item.dimension for item in valid.criteria} == {
        RFQEvaluationDimension.TECHNICAL,
        RFQEvaluationDimension.COMMERCIAL,
    }

    invalid = [
        [dict(_criteria()[0], code="Same"), dict(_criteria()[1], code=" same ")],
        [dict(_criteria()[0], weight_percent="59.99"), _criteria()[1]],
        [dict(_criteria()[0], dimension="COMMERCIAL"), _criteria()[1]],
        [dict(_criteria()[0], weight_percent="NaN"), _criteria()[1]],
        [dict(_criteria()[0], weight_percent="60.001"), _criteria()[1]],
    ]
    for criteria in invalid:
        with pytest.raises(ValueError):
            RFQEvaluationMatrixCreate(criteria=criteria)


def test_evaluation_submission_rejects_duplicate_and_invalid_scores_or_gate_shape():
    criterion_id = "2e706fc0-9f6c-4b0b-a7cf-6a9d9a579afe"
    with pytest.raises(ValueError):
        RFQResponseEvaluationSubmit(evaluations=[
            {"criterion_id": criterion_id, "score": "50"},
            {"criterion_id": criterion_id, "score": "60"},
        ])
    for score in ("-0.01", "100.01", "NaN", "Infinity", "1.001"):
        with pytest.raises(ValueError):
            RFQResponseEvaluationSubmit(evaluations=[{"criterion_id": criterion_id, "score": score}])


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires task-owned disposable PostgreSQL")
async def test_matrix_scoring_gate_revision_history_and_scope():
    _require_task_database()
    suffix = uuid4().hex[:16]
    supplier = Supplier(code=f"M34T003-{suffix}", name="Synthetic evaluation supplier", is_active=True)
    actor = User(
        email=f"m34-t003-{suffix}@example.invalid",
        username=f"m34t003-{suffix}",
        full_name="Synthetic Procurement Evaluator",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    rfq_id = None
    async with AsyncSessionLocal() as db:
        db.add_all([supplier, actor])
        await db.flush()
        supplier_id = supplier.id
        actor_id = actor.id
        rfq = RFQRequest(
            rfq_no=f"M34-T003-{suffix}",
            title="Synthetic weighted bid comparison",
            quantity=Decimal("10.00"),
            unit="KG",
            status=RFQStatus.SENT,
        )
        db.add(rfq)
        await db.flush()
        rfq_id = rfq.id
        response = RFQResponse(
            rfq_id=rfq.id,
            supplier_id=supplier.id,
            quoted_unit_price=Decimal("12.5000"),
            invitation_status=RFQInvitationStatus.ISSUED,
            invitation_issued_at=datetime.now(timezone.utc),
            status=RFQResponseStatus.PENDING,
        )
        db.add(response)
        await db.commit()
        response_id = response.id

        try:
            read_only_actor = SimpleNamespace(id=uuid4(), is_superuser=False, roles=[])
            with pytest.raises(HTTPException) as denied_matrix:
                await create_rfq_evaluation_matrix(
                    rfq.id,
                    RFQEvaluationMatrixCreate(criteria=_criteria()),
                    db,
                    read_only_actor,
                )
            assert denied_matrix.value.status_code == 403
            with pytest.raises(HTTPException) as denied_detail:
                await get_rfq(rfq.id, db, read_only_actor)
            assert denied_detail.value.status_code == 403

            criteria = await create_rfq_evaluation_matrix(
                rfq.id,
                RFQEvaluationMatrixCreate(criteria=_criteria()),
                db,
                actor,
            )
            assert len(criteria) == 2
            with pytest.raises(HTTPException) as immutable:
                await create_rfq_evaluation_matrix(
                    rfq.id,
                    RFQEvaluationMatrixCreate(criteria=_criteria()),
                    db,
                    actor,
                )
            assert immutable.value.status_code == 409

            bid = await add_rfq_response(
                rfq.id,
                RFQResponseCreate(
                    supplier_id=supplier_id,
                    quoted_unit_price="12.5000",
                    quoted_currency="KES",
                    lead_time_days=4,
                ),
                db,
                actor,
            )
            assert bid.status == RFQResponseStatus.SUBMITTED
            assert bid.submitted_by_id == actor_id

            by_code = {criterion.code: criterion for criterion in criteria}
            with pytest.raises(HTTPException) as missing_gate:
                await submit_rfq_response_evaluations(
                    rfq.id,
                    response.id,
                    RFQResponseEvaluationSubmit(evaluations=[
                        {"criterion_id": by_code["TECHNICAL_FIT"].id, "score": "80"},
                        {"criterion_id": by_code["COMMERCIAL_VALUE"].id, "score": "90"},
                    ]),
                    db,
                    actor,
                )
            assert missing_gate.value.status_code == 422

            with pytest.raises(HTTPException) as unexpected_gate:
                await submit_rfq_response_evaluations(
                    rfq.id,
                    response.id,
                    RFQResponseEvaluationSubmit(evaluations=[
                        {"criterion_id": by_code["TECHNICAL_FIT"].id, "score": "80", "passes_gate": True},
                        {"criterion_id": by_code["COMMERCIAL_VALUE"].id, "score": "90", "passes_gate": True},
                    ]),
                    db,
                    actor,
                )
            assert unexpected_gate.value.status_code == 422

            first = await submit_rfq_response_evaluations(
                rfq.id,
                response.id,
                RFQResponseEvaluationSubmit(evaluations=[
                    {"criterion_id": by_code["TECHNICAL_FIT"].id, "score": "80", "passes_gate": False, "comments": "Synthetic failed gate."},
                    {"criterion_id": by_code["COMMERCIAL_VALUE"].id, "score": "90"},
                ]),
                db,
                actor,
            )
            assert {item.revision_no for item in first} == {1}
            assert all(item.evaluator_id == actor_id for item in first)
            persisted_response = await db.get(RFQResponse, response_id, populate_existing=True)
            assert persisted_response.score == Decimal("84.00")
            assert persisted_response.evaluation_status == RFQEvaluationStatus.DISQUALIFIED

            second = await submit_rfq_response_evaluations(
                rfq.id,
                response.id,
                RFQResponseEvaluationSubmit(evaluations=[
                    {"criterion_id": by_code["TECHNICAL_FIT"].id, "score": "100", "passes_gate": True},
                    {"criterion_id": by_code["COMMERCIAL_VALUE"].id, "score": "75"},
                ]),
                db,
                actor,
            )
            assert {item.revision_no for item in second} == {1, 2}
            persisted_response = await db.get(RFQResponse, response_id, populate_existing=True)
            assert persisted_response.score == Decimal("90.00")
            assert persisted_response.evaluation_status == RFQEvaluationStatus.QUALIFIED
            history_count = await db.scalar(
                select(func.count()).select_from(RFQResponseEvaluation).where(
                    RFQResponseEvaluation.response_id == response.id
                )
            )
            assert history_count == 4

            db.expire(rfq, ["evaluation_criteria"])
            detail = await get_rfq(rfq.id, db, actor)
            response_read = next(item for item in detail.responses if item.id == response.id)
            assert response_read.score == Decimal("90.00")
            assert response_read.evaluation_status == RFQEvaluationStatus.QUALIFIED
            assert {item.revision_no for item in response_read.evaluations} == {2}
            assert {item.revision_no for item in response_read.evaluation_history} == {1, 2}
            assert all(item.evaluator_id == actor_id for item in response_read.evaluation_history)
            assert {item.dimension for item in detail.evaluation_criteria} == {
                RFQEvaluationDimension.TECHNICAL,
                RFQEvaluationDimension.COMMERCIAL,
            }
        finally:
            await db.rollback()
            await db.execute(delete(RFQResponseEvaluation).where(RFQResponseEvaluation.response_id == response_id))
            await db.execute(delete(RFQEvaluationCriterion).where(RFQEvaluationCriterion.rfq_id == rfq_id))
            await db.execute(delete(RFQResponse).where(RFQResponse.id == response_id))
            await db.execute(delete(RFQRequest).where(RFQRequest.id == rfq_id))
            await db.execute(delete(Supplier).where(Supplier.id == supplier_id))
            await db.execute(delete(User).where(User.id == actor_id))
            await db.commit()
