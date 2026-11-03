"""M34.S03.T004 linkage integration; writes only to a guarded task-owned PostgreSQL DB."""
from __future__ import annotations

import os
import re
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.engine import URL

from app.api.v1.endpoints import procurement as procurement_endpoint
from app.api.v1.endpoints import qms as qms_endpoint
from app.db.session import AsyncSessionLocal, engine
from app.models.master import Supplier
from app.models.procurement import SupplierEvaluation
from app.models.quality import QCDeviation, QCInspection, QCType, CorrectiveAction
from app.models.user import User
from app.schemas.qms import CorrectiveActionCreate, CorrectiveActionStepCreate, CorrectiveActionUpdate


TASK_DB_ENV = "M34_S03_T004_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S03_T004_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s03_t004_[a-f0-9]{24}")


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
        pytest.skip(f"Run only with {TASK_DB_ENV}=1 for this task's disposable PostgreSQL database.")
    if not _is_task_database(engine.url, expected_name):
        pytest.fail("Refusing integration writes: DATABASE_URL must match this task's passwordless loopback database.")


def test_database_guard_accepts_only_the_exact_passwordless_loopback_target():
    name = "fmcg_m34_s03_t004_0123456789abcdef01234567"
    assert _is_task_database(URL.create("postgresql+asyncpg", host="127.0.0.1", database=name), name)
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="erp", password="secret", host="127.0.0.1", database=name), name
    )
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.invalid", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires this task's disposable PostgreSQL database")
async def test_supplier_evaluation_and_inspection_links_are_consistent_and_permission_gated():
    _require_task_database()
    suffix = uuid4().hex[:20]
    actor = User(
        email=f"m34-s03-t004-{suffix}@example.invalid",
        username=f"m34s03t004{suffix}",
        full_name="Synthetic quality reviewer",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    supplier = Supplier(code=f"M34T004-{suffix}", name="Synthetic supplier")
    other_supplier = Supplier(code=f"M34T004-X{suffix}", name="Other synthetic supplier")
    async with AsyncSessionLocal() as db:
        db.add_all([actor, supplier, other_supplier])
        await db.flush()
        evaluation = SupplierEvaluation(
            supplier_id=supplier.id,
            evaluation_date=date.today(),
            on_time_delivery_score=80,
            quality_score=90,
            price_competitiveness_score=70,
            responsiveness_score=85,
            overall_score=81.25,
            evaluator_id=actor.id,
            notes="Synthetic task acceptance evaluation",
        )
        inspection = QCInspection(
            inspection_no=f"M34T004-QC-{suffix}",
            qc_type=QCType.INCOMING,
            inspection_date=date.today(),
            supplier_id=supplier.id,
        )
        db.add_all([evaluation, inspection])
        await db.flush()
        deviation = QCDeviation(
            deviation_no=f"M34T004-DEV-{suffix}",
            inspection_id=inspection.id,
            deviation_type="SUPPLIER_QUALITY",
            description="Synthetic incoming inspection deviation",
            reported_by_id=actor.id,
        )
        db.add(deviation)
        await db.flush()

        linked = await qms_endpoint.create_corrective_action(
            CorrectiveActionCreate(
                title="Synthetic supplier corrective action",
                description="Investigate and record the synthetic supplier issue.",
                supplier_id=supplier.id,
                supplier_evaluation_id=evaluation.id,
                steps=[CorrectiveActionStepCreate(step_no=1, step_description="Document synthetic containment.")],
            ),
            db,
            actor,
        )
        assert linked.supplier_id == supplier.id
        assert linked.supplier_evaluation_id == evaluation.id
        assert linked.supplier_name == supplier.name

        quality_editor = SimpleNamespace(
            id=actor.id,
            is_superuser=False,
            roles=[SimpleNamespace(
                is_active=True,
                permissions=[SimpleNamespace(is_active=True, code="quality.edit")],
            )],
        )
        with pytest.raises(HTTPException) as verify_denied:
            await qms_endpoint.verify_corrective_action(
                linked.id, "Synthetic effectiveness review", db, quality_editor
            )
        assert verify_denied.value.status_code == 403
        with pytest.raises(HTTPException) as direct_verify_denied:
            await qms_endpoint.update_corrective_action(
                linked.id, CorrectiveActionUpdate(status="VERIFIED"), db, quality_editor
            )
        assert direct_verify_denied.value.status_code == 409
        with pytest.raises(HTTPException) as direct_pdca_denied:
            await qms_endpoint.update_corrective_action(
                linked.id, CorrectiveActionUpdate(pdca_closed_at=None), db, actor
            )
        assert direct_pdca_denied.value.status_code == 409
        completed = await qms_endpoint.complete_ca_step(
            linked.id, linked.steps[0].id, "Synthetic containment documented", db, quality_editor
        )
        assert completed.steps_completed == 1
        verified = await qms_endpoint.verify_corrective_action(
            linked.id, "Synthetic effectiveness evidence", db, actor
        )
        assert verified.status == "VERIFIED"
        with pytest.raises(HTTPException) as revert_denied:
            await qms_endpoint.update_corrective_action(
                linked.id, CorrectiveActionUpdate(status="OPEN"), db, quality_editor
            )
        assert revert_denied.value.status_code == 409
        closed = await qms_endpoint.close_pdca(linked.id, db, actor)
        assert closed.pdca_closed_at is not None
        with pytest.raises(HTTPException) as clear_denied:
            await qms_endpoint.update_corrective_action(
                linked.id, CorrectiveActionUpdate(pdca_closed_at=None), db, actor
            )
        assert clear_denied.value.status_code == 409

        listed = await qms_endpoint.list_corrective_actions(
            status=None,
            severity=None,
            assigned_to_id=None,
            supplier_id=supplier.id,
            supplier_evaluation_id=evaluation.id,
            db=db,
            current_user=actor,
        )
        assert [row.id for row in listed] == [linked.id]

        with pytest.raises(HTTPException) as mismatch:
            await qms_endpoint.create_corrective_action(
                CorrectiveActionCreate(
                    title="Mismatched source must be rejected",
                    description="Supplier and evaluation do not agree.",
                    supplier_id=other_supplier.id,
                    supplier_evaluation_id=evaluation.id,
                ),
                db,
                actor,
            )
        assert mismatch.value.status_code == 422

        with pytest.raises(HTTPException) as hidden:
            await qms_endpoint.get_corrective_action(linked.id, db, User(
                email=f"m34-s03-t004-reader-{suffix}@example.invalid",
                username=f"m34s03t004reader{suffix}",
                full_name="Synthetic unprivileged reader",
                hashed_password="not-a-login-credential",
                is_active=True,
                is_superuser=False,
            ))
        assert hidden.value.status_code == 403
        hidden_list = await qms_endpoint.list_corrective_actions(
            status=None,
            severity=None,
            assigned_to_id=None,
            supplier_id=None,
            supplier_evaluation_id=None,
            db=db,
            current_user=User(
                email=f"m34-s03-t004-list-reader-{suffix}@example.invalid",
                username=f"m34s03t004listreader{suffix}",
                full_name="Synthetic unprivileged list reader",
                hashed_password="not-a-login-credential",
                is_active=True,
                is_superuser=False,
            ),
        )
        assert all(action.supplier_id is None for action in hidden_list)

        auto_linked = await qms_endpoint.create_deviation_corrective_action(
            deviation.id,
            CorrectiveActionCreate(
                title="Synthetic deviation CAPA",
                description="Supplier is inherited from the incoming inspection.",
            ),
            db,
            actor,
        )
        assert auto_linked.supplier_id == supplier.id
        assert auto_linked.supplier_evaluation_id is None

        stored = await db.scalar(
            select(CorrectiveAction).where(CorrectiveAction.id == auto_linked.id)
        )
        assert stored is not None and stored.supplier_id == supplier.id

        scorecard = await procurement_endpoint.supplier_dashboard(db, actor)
        supplier_row = next(row for row in scorecard if row.supplier_id == supplier.id)
        assert supplier_row.supplier_capa_count == 2
        assert supplier_row.supplier_open_capa_count == 1
        assert supplier_row.supplier_capa_signals_restricted is False

        procurement_only = SimpleNamespace(
            is_superuser=False,
            roles=[SimpleNamespace(
                is_active=True,
                permissions=[SimpleNamespace(is_active=True, code="procurement.view_all")],
            )],
        )
        restricted_scorecard = await procurement_endpoint.supplier_dashboard(db, procurement_only)
        restricted_row = next(row for row in restricted_scorecard if row.supplier_id == supplier.id)
        assert restricted_row.supplier_capa_count is None
        assert restricted_row.supplier_open_capa_count is None
        assert restricted_row.supplier_capa_signals_restricted is True
