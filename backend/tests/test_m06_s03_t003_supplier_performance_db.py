"""M06.S03.T003 synthetic PostgreSQL verification of supplier score completeness."""
from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL

from app.crud.procurement import average_supplier_score, create_evaluation, list_evaluations
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Supplier
from app.models.procurement import SupplierEvaluation
from app.models.user import User
from app.schemas.procurement import SupplierEvaluationCreate


pytestmark = pytest.mark.skipif(
    os.environ.get("M06_S03_T003_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m06_s03_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    if os.environ.get("M06_S03_T003_DISPOSABLE_TEST_DATABASE") != "1":
        pytest.skip("Set M06_S03_T003_DISPOSABLE_TEST_DATABASE=1 only for this task-owned disposable PostgreSQL database.")
    expected = os.environ.get("M06_S03_T003_DISPOSABLE_TEST_DATABASE_NAME")
    if not _is_task_database(engine.url, expected):
        pytest.fail("Refusing integration writes: DATABASE_URL must match the exact loopback M06.S03.T003 database without a password.")
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m06_s03_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m06_s03_t003_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m06_s03_t003_short")
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="postgres", password="never-used", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


def _evaluation_payload(supplier_id, day: date, scores: tuple[str, str, str, str]) -> dict:
    delivery, quality, price, responsiveness = scores
    return {
        "supplier_id": supplier_id,
        "evaluation_date": day,
        "on_time_delivery_score": Decimal(delivery),
        "quality_score": Decimal(quality),
        "price_competitiveness_score": Decimal(price),
        "responsiveness_score": Decimal(responsiveness),
    }


def test_evaluation_create_schema_requires_all_four_dimensions_and_date():
    fields = SupplierEvaluationCreate.model_fields
    for field in (
        "evaluation_date",
        "on_time_delivery_score",
        "quality_score",
        "price_competitiveness_score",
        "responsiveness_score",
    ):
        assert fields[field].is_required()
    assert SupplierEvaluation.__table__.columns["evaluation_date"].nullable is False
    for field in (
        "on_time_delivery_score",
        "quality_score",
        "price_competitiveness_score",
        "responsiveness_score",
        "overall_score",
    ):
        assert SupplierEvaluation.__table__.columns[field].nullable is False


@pytest.mark.asyncio
async def test_supplier_master_score_matches_all_persisted_evaluations():
    expected_database = _require_task_database()
    suffix = uuid4().hex[:16]
    async with AsyncSessionLocal() as db:
        assert (await db.execute(text("SELECT current_database()"))).scalar_one() == expected_database
        user = User(
            email=f"m06-t003-{suffix}@example.invalid",
            username=f"m06t003{suffix}",
            full_name="Synthetic M06 T003 evaluator",
            hashed_password="synthetic-test-only-not-a-credential",
        )
        supplier = Supplier(code=f"M06-T003-S-{suffix}", name="Synthetic supplier M06 T003")
        db.add_all([user, supplier])
        await db.flush()
        supplier_id = supplier.id
        user_id = user.id
        await db.commit()

        first = await create_evaluation(
            db,
            _evaluation_payload(supplier_id, date(2026, 10, 28), ("79", "79", "79", "79")),
            user_id,
        )
        assert first.overall_score == Decimal("79")
        await db.commit()
        await db.refresh(supplier)
        assert supplier.performance_score == Decimal("79.00")

        second = await create_evaluation(
            db,
            _evaluation_payload(supplier_id, date(2026, 10, 29), ("79.33", "79.33", "79.34", "79.32")),
            user_id,
        )
        assert second.overall_score == Decimal("79.33")
        await db.commit()
        await db.refresh(supplier)

        evaluations = await list_evaluations(db, supplier_id=supplier_id)
        assert len(evaluations) == 2
        assert {evaluation.evaluator_id for evaluation in evaluations} == {user_id}
        assert all(evaluation.evaluation_date is not None for evaluation in evaluations)
        assert all(
            score is not None
            for evaluation in evaluations
            for score in (
                evaluation.on_time_delivery_score,
                evaluation.quality_score,
                evaluation.price_competitiveness_score,
                evaluation.responsiveness_score,
                evaluation.overall_score,
            )
        )
        unrounded_history_average = await db.scalar(
            select(func.avg(SupplierEvaluation.overall_score)).where(
                SupplierEvaluation.supplier_id == supplier_id
            )
        )
        assert unrounded_history_average == Decimal("79.165")
        history_average = await average_supplier_score(db, supplier_id)
        assert history_average == Decimal("79.17")
        assert supplier.performance_score == history_average
