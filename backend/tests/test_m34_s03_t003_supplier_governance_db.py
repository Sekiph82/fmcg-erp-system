"""M34.S03.T003 PostgreSQL persistence and procurement-gate acceptance."""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.engine import URL

from app.api.v1.endpoints import procurement as procurement_endpoint
from app.api.v1.endpoints import suppliers as suppliers_endpoint
from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.master import Supplier, SupplierQualificationStatus
from app.models.procurement import PurchaseOrder
from app.models.user import User
from app.schemas.master import SupplierPreferenceDecision, SupplierQualificationDecision
from app.schemas.procurement import POCreate


TASK_DB_ENV = "M34_S03_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = "M34_S03_T003_DISPOSABLE_TEST_DATABASE_NAME"
TASK_DB_PATTERN = re.compile(r"fmcg_m34_s03_t003_[a-f0-9]{24}")


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


def test_task_database_guard_rejects_non_disposable_targets():
    name = "fmcg_m34_s03_t003_0123456789abcdef01234567"
    assert _is_task_database(URL.create("postgresql+asyncpg", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", username="erp", password="secret", host="127.0.0.1", database=name), name)
    assert not _is_task_database(URL.create("postgresql+asyncpg", host="db.invalid", database=name), name)
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.skipif(os.environ.get(TASK_DB_ENV) != "1", reason="requires this task's disposable PostgreSQL database")
async def test_qualification_and_preference_are_audited_and_pending_supplier_cannot_create_po(monkeypatch):
    _require_task_database()
    suffix = uuid4().hex[:16]
    today = date.today()
    actor = User(
        email=f"m34-s03-t003-{suffix}@example.invalid",
        username=f"m34s03t003{suffix}",
        full_name="Synthetic governance approver",
        hashed_password="not-a-login-credential",
        is_active=True,
        is_superuser=True,
    )
    supplier = Supplier(
        code=f"M34S03T003-{suffix}",
        name="Synthetic pending supplier",
        qualification_status=SupplierQualificationStatus.PENDING,
        is_active=True,
        is_preferred=False,
    )
    async with AsyncSessionLocal() as db:
        db.add_all([actor, supplier])
        await db.flush()

        await suppliers_endpoint.decide_supplier_qualification(
            supplier.id,
            SupplierQualificationDecision(
                qualification_status=SupplierQualificationStatus.APPROVED,
                approved_from=today,
                approved_until=today + timedelta(days=10),
                reason="Synthetic qualification evidence recorded",
            ),
            db,
            actor,
        )
        assert supplier.qualification_status == SupplierQualificationStatus.APPROVED
        assert supplier.approved_by_id == actor.id
        assert supplier.approved_at is not None

        await suppliers_endpoint.decide_supplier_preference(
            supplier.id,
            SupplierPreferenceDecision(is_preferred=True, reason="Synthetic preferred-list decision"),
            db,
            actor,
        )
        assert supplier.is_preferred is True

        monkeypatch.setattr(procurement_endpoint, "_require_procurement_action", lambda *_args, **_kwargs: None)
        po_body = POCreate(
            po_no=f"M34S03T003-PO-{suffix}",
            supplier_id=supplier.id,
            order_date=today,
            expected_delivery_date=today + timedelta(days=11),
            currency="KES",
        )
        with pytest.raises(HTTPException) as blocked:
            await procurement_endpoint.create_po(po_body, db, actor)
        assert blocked.value.status_code == 409
        assert "expires" in blocked.value.detail

        await suppliers_endpoint.decide_supplier_qualification(
            supplier.id,
            SupplierQualificationDecision(
                qualification_status=SupplierQualificationStatus.SUSPENDED,
                reason="Synthetic temporary hold",
            ),
            db,
            actor,
        )
        assert supplier.qualification_status == SupplierQualificationStatus.SUSPENDED
        assert supplier.is_preferred is False
        assert supplier.approved_by_id is None
        assert supplier.approved_at is None

        events = (
            await db.execute(
                select(AuditLog)
                .where(AuditLog.target_type == "suppliers", AuditLog.target_id == str(supplier.id))
                .order_by(AuditLog.created_at)
            )
        ).scalars().all()
        assert [event.details["workflow"] for event in events] == [
            "SUPPLIER_QUALIFICATION_DECISION",
            "SUPPLIER_PREFERENCE_DECISION",
            "SUPPLIER_QUALIFICATION_DECISION",
        ]
        assert events[0].details["reason"] == "Synthetic qualification evidence recorded"
        assert events[0].details["approval_required"] is True
        assert events[1].details["decision"] == "PREFERRED"
        assert events[2].details["decision"] == "SUSPENDED"
        assert await db.scalar(select(PurchaseOrder.id).where(PurchaseOrder.po_no == po_body.po_no)) is None
