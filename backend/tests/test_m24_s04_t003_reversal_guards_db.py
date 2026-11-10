"""M24.S04.T003 generic reversal fail-closed checks for disposable PostgreSQL."""
from __future__ import annotations

import os
import re
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.engine import URL

from app.db.session import AsyncSessionLocal, engine
from app.models.material_flow import (
    FlowMode,
    FlowStatus,
    FlowType,
    MaterialFlowTransaction,
)
from app.schemas.material_flow import FlowTransactionCreate
from app.services import material_flow_service


TASK_DB_ENV = "M24_S04_T003_DISPOSABLE_TEST_DATABASE"
TASK_DB_NAME_ENV = f"{TASK_DB_ENV}_NAME"
pytestmark = pytest.mark.skipif(
    os.environ.get(TASK_DB_ENV) != "1",
    reason=f"requires this task's disposable PostgreSQL database ({TASK_DB_ENV}=1)",
)


def _is_task_database(url, expected_name: str | None) -> bool:
    return (
        url.drivername in {"postgresql", "postgresql+asyncpg"}
        and url.host in {"127.0.0.1", "localhost", "::1"}
        and url.password is None
        and isinstance(expected_name, str)
        and re.fullmatch(r"fmcg_m24_s04_t003_[a-f0-9]{20,32}", expected_name) is not None
        and url.database == expected_name
    )


def _require_task_database() -> str:
    expected = os.environ.get(TASK_DB_NAME_ENV)
    if os.environ.get(TASK_DB_ENV) != "1" or not _is_task_database(engine.url, expected):
        pytest.fail(
            "Refusing integration writes: DATABASE_URL must match this exact loopback M24.S04.T003 disposable database without a password."
        )
    return expected


def test_database_guard_requires_exact_loopback_task_database():
    name = "fmcg_m24_s04_t003_0123456789abcdef0123"
    safe = URL.create("postgresql+asyncpg", username="postgres", host="127.0.0.1", database=name)
    assert _is_task_database(safe, name)
    assert not _is_task_database(safe, "fmcg_m24_s04_t003_0123456789abcdef0124")
    assert not _is_task_database(safe, "fmcg_m24_s04_t003_short")
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", host="db.example.com", database=name), name
    )
    assert not _is_task_database(
        URL.create("postgresql+asyncpg", username="postgres", password="unused", host="127.0.0.1", database=name), name
    )
    assert not _is_task_database(URL.create("sqlite+aiosqlite", database=name), name)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_engine_after_test():
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_generic_reversal_service_paths_preserve_source_and_write_no_reversal():
    _require_task_database()
    suffix = uuid4().hex[:20]
    actor_id = uuid4()
    async with AsyncSessionLocal() as db:
        original = MaterialFlowTransaction(
            flow_no=f"M24-T003-ORIG-{suffix}",
            flow_type=FlowType.TANK_TRANSFER,
            flow_mode=FlowMode.ONE_STEP,
            status=FlowStatus.POSTED,
            notes="Synthetic posted transaction for reversal guard",
        )
        reversal_draft = MaterialFlowTransaction(
            flow_no=f"M24-T003-REV-{suffix}",
            flow_type=FlowType.REVERSAL,
            flow_mode=FlowMode.ONE_STEP,
            status=FlowStatus.DRAFT,
            notes="Synthetic draft that must remain unposted",
        )
        db.add_all([original, reversal_draft])
        await db.commit()
        original_id = original.id
        reversal_draft_id = reversal_draft.id

        with pytest.raises(ValueError, match="Generic reversal is unavailable"):
            await material_flow_service.reverse_flow_transaction(db, original_id, actor_id)
        with pytest.raises(ValueError, match="cannot be posted"):
            await material_flow_service.confirm_flow_transaction(db, reversal_draft_id, actor_id)
        with pytest.raises(ValueError, match="Generic REVERSAL transactions are disabled"):
            await material_flow_service.create_flow_transaction(
                db, FlowTransactionCreate(flow_type=FlowType.REVERSAL), actor_id
            )
        await db.rollback()

    async with AsyncSessionLocal() as verify:
        original = await verify.get(MaterialFlowTransaction, original_id)
        reversal_draft = await verify.get(MaterialFlowTransaction, reversal_draft_id)
        reversal_count = await verify.scalar(
            select(func.count(MaterialFlowTransaction.id)).where(
                MaterialFlowTransaction.source_document_type == "REVERSAL",
                MaterialFlowTransaction.flow_no.like(f"M24-T003-%-{suffix}"),
            )
        )
        assert original is not None and original.status == FlowStatus.POSTED
        assert reversal_draft is not None and reversal_draft.status == FlowStatus.DRAFT
        assert reversal_count == 0
