"""Gate-definition storage checks on a task-owned disposable PostgreSQL database."""
from __future__ import annotations

import os
import re
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionLocal, engine
from app.models.quality import QualityGateDefinition
from app.services.qms_service import create_quality_gate_definition, list_quality_gate_definitions


pytestmark = pytest.mark.skipif(
    os.environ.get("M27_S01_T001_DISPOSABLE_TEST_DATABASE") != "1",
    reason="requires the task-owned disposable PostgreSQL runner",
)


@pytest_asyncio.fixture(autouse=True)
async def _dispose_async_engine_after_test():
    yield
    await engine.dispose()


async def _assert_task_database(db) -> None:
    expected = os.environ.get("M27_S01_T001_DISPOSABLE_TEST_DATABASE_NAME", "")
    assert engine.url.drivername in {"postgresql", "postgresql+asyncpg"}
    assert engine.url.host in {"127.0.0.1", "localhost", "::1"}
    assert re.fullmatch(r"fmcg_m27_s01_t001_[a-f0-9]{20,32}", expected)
    actual = (await db.execute(text("SELECT current_database()"))).scalar_one()
    assert actual == expected


@pytest.mark.asyncio
async def test_gate_definition_can_be_configured_and_filtered_by_trigger_and_module():
    suffix = uuid4().hex[:16].upper()
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        created = await create_quality_gate_definition(
            db,
            {
                "code": f"TEST_GATE_{suffix}",
                "name": "Synthetic receiving gate",
                "gate_type": "MATERIAL_QUALITY",
                "trigger_event": "ON_RECEIPT",
                "target_module": "procurement",
                "description": "Synthetic test configuration only",
                "is_active": True,
            },
        )
        await db.commit()

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        found = await list_quality_gate_definitions(
            db, trigger_event="ON_RECEIPT", target_module="procurement"
        )
        assert [item.code for item in found] == [f"TEST_GATE_{suffix}"]
        assert found[0].id == created.id


@pytest.mark.asyncio
async def test_gate_definition_codes_are_unique_in_the_database():
    code = f"UNIQUE_GATE_{uuid4().hex[:16].upper()}"
    data = {
        "code": code,
        "name": "Synthetic unique gate",
        "gate_type": "MATERIAL_QUALITY",
        "trigger_event": "ON_RECEIPT",
        "target_module": "procurement",
        "is_active": True,
    }
    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        await create_quality_gate_definition(db, dict(data))
        await db.commit()

    async with AsyncSessionLocal() as db:
        await _assert_task_database(db)
        duplicate = QualityGateDefinition(**data)
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()
        existing = await db.scalar(
            select(QualityGateDefinition).where(QualityGateDefinition.code == code)
        )
        assert existing is not None
